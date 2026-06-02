"""PHASE 0 PORTFOLIO PARITY GATE — prove risk_manager.simulate_portfolio == the validated overlay.

The portfolio overlay (RPT 0.35%, max 15, bear-sizing 0.25x, 15% DD breaker, idle cash,
momentum-rank selection, NSE costs) was validated as a `portfolio()` function inside the
research scripts. This gate freezes that exact function as the GOLDEN reference, then
asserts the extracted `backend.engine.runtime.risk_manager.simulate_portfolio` reproduces
it **curve-for-curve** (equity identical every session) on the full v2 trade set.

It also prints the headline metrics, which must reproduce the validated v2:
FULL ~= 26.5% CAGR / 14.8% maxDD / 1.79 Calmar / 19.5% ex-2021.

    python scripts/run_portfolio_parity.py
"""
import sqlite3
import sys
import warnings
from collections import OrderedDict, defaultdict
from datetime import date
from decimal import Decimal
from math import sqrt
from statistics import median

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars        # noqa: E402
from backend.engine.costs import CostModel                                # noqa: E402
from backend.engine.precompute import precompute_features                 # noqa: E402
from backend.engine.regime import load_regime                             # noqa: E402
from backend.engine.runtime import risk_manager                           # noqa: E402
from backend.engine.runtime.config import RISK_V2, STRATEGY_V2            # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
START_CAP = Decimal("100000")
DAILY_YIELD = (1 + 0.065) ** (1 / 252) - 1
RPT = 0.35
CR = 1e7
cm = CostModel()


def slip(a):
    return Decimal("0.0010") if a >= 15 else Decimal("0.0025") if a >= 5 else Decimal("0.0050") if a >= 1 else Decimal("0.0100")


# ---- build the full v2 trade set + lookups (identical to run_v2_deployable_tiers) ----
regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
close_lookup, score_lookup = {}, {}
trades = []
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    close_lookup[s] = {b.date: b.close for b in bs}
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    sl = slip(median(tnv) / CR if tnv else 0)
    c = df["close"].astype(float).to_numpy()
    r126 = np.full(len(c), np.nan); r252 = np.full(len(c), np.nan)
    r126[126:] = c[126:] / c[:-126] - 1
    r252[252:] = c[252:] / c[:-252] - 1
    dret = np.diff(c) / c[:-1]
    vol = np.full(len(c), np.nan)
    for k in range(252, len(c)):
        sd = dret[k - 252:k].std(); vol[k] = sd if sd > 0 else np.nan
    sc = 0.5 * (r126 / vol) + 0.5 * (r252 / vol)
    for k in range(len(bs) - 1):
        if sc[k] == sc[k]:
            score_lookup[(s, bs[k + 1].date)] = float(sc[k])
    tr = _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0,
                        chandelier_mult=float(STRATEGY_V2.chandelier_mult), slippage=sl,
                        min_trp=STRATEGY_V2.min_trp, start_date=START, use_regime=False,
                        skip_circuit_locked=STRATEGY_V2.skip_circuit_locked,
                        vol_breakout_k=STRATEGY_V2.vol_breakout_k)
    trades.extend(tr)
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()

FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


# ---- GOLDEN reference: the validated portfolio() overlay, frozen verbatim -------------
def portfolio_reference(trades, cal, *, dd_halt=0.15, bear_frac=0.25, max_pos=15):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    for d in eo:
        eo[d].sort(key=lambda t: score_lookup.get((t.symbol, t.entry_date), -1e9), reverse=True)
    rpt = Decimal(str(RPT)); resume = dd_halt * 0.5
    cash = START_CAP; op = []; curve = []; peak = float(START_CAP); halted = False
    for d in cal:
        cash *= Decimal(1 + DAILY_YIELD)
        still = []
        for p in op:
            if p["xd"] == d:
                pr = Decimal(p["sh"]) * p["xp"]; cash += pr - cm.sell_costs(pr)
            else:
                still.append(p)
        op = still
        for p in op:
            p["px"] = lc(p["s"], d, p["px"])
        eq = cash + sum(Decimal(p["sh"]) * p["px"] for p in op)
        peak = max(peak, float(eq))
        if float(eq) < peak * (1 - dd_halt):
            halted = True
        elif float(eq) > peak * (1 - resume):
            halted = False
        if not halted:
            mult = Decimal("1.0") if regime_map.get(d, False) else Decimal(str(bear_frac))
            for t in eo.get(d, []):
                if len(op) >= max_pos:
                    continue
                sh = int((eq * rpt * mult / Decimal(100)) / t.stopdist)
                if sh <= 0:
                    continue
                cost = Decimal(sh) * t.entry; tot = cost + cm.buy_costs(cost)
                if tot > cash:
                    continue
                cash -= tot
                op.append({"s": t.symbol, "sh": sh, "xd": t.exit_date, "xp": t.exit, "px": t.entry})
        eq = cash + sum(Decimal(p["sh"]) * p["px"] for p in op)
        curve.append((d, float(eq)))
    return curve


def met(curve, cal):
    vals = [v for _, v in curve]
    yrs = (cal[-1] - cal[0]).days / 365.25
    cagr = (vals[-1] / vals[0]) ** (1 / yrs) - 1
    pk = vals[0]; mdd = 0
    for v in vals:
        pk = max(pk, v); mdd = max(mdd, (pk - v) / pk)
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    m = sum(rets) / len(rets); var = sum((x - m) ** 2 for x in rets) / len(rets)
    return cagr, mdd, (cagr / mdd if mdd else 0), (m / sqrt(var) * sqrt(252) if var > 0 else 0)


def ex2021_cagr(curve):
    end = OrderedDict()
    for d, v in curve:
        end[d.year] = v
    ys = OrderedDict(); prev = float(START_CAP)
    for y, v in end.items():
        ys[y] = v / prev - 1; prev = v
    span = (FULL[-1] - FULL[0]).days / 365.25 - 1.0
    fac = 1.0
    for y, r in ys.items():
        if y != 2021:
            fac *= (1 + r)
    return fac ** (1 / span) - 1


# ---- run both and compare curve-for-curve --------------------------------------------
ref = portfolio_reference(trades, FULL)
rt = risk_manager.simulate_portfolio(
    trades, FULL, params=RISK_V2, regime_on=regime_map, momentum_score=score_lookup,
    close_on=close_lookup, start_capital=START_CAP, cost_model=cm,
)

mismatches = [(d1, v1, v2) for (d1, v1), (_, v2) in zip(ref, rt) if v1 != v2]
print(f"v2 trades         : {len(trades)}")
print(f"calendar sessions : {len(FULL)}")
print(f"reference final Rs: {ref[-1][1]:,.2f}")
print(f"runtime   final Rs: {rt[-1][1]:,.2f}")
print(f"curve mismatches  : {len(mismatches)} / {len(ref)} sessions")
if mismatches:
    d, v1, v2 = mismatches[0]
    print(f"first diff @ {d}: reference={v1:,.6f}  runtime={v2:,.6f}")

cagr, mdd, cal_, shp = met(rt, FULL)
print(f"\nFULL v2 (runtime overlay): CAGR {cagr:.1%} | maxDD {mdd:.1%} | Calmar {cal_:.2f} "
      f"| Sharpe {shp:.2f} | ex-2021 {ex2021_cagr(rt):.1%}")
print("  (validated headline: 26.5% / 14.8% / 1.79 / 19.5%)")

ok = len(mismatches) == 0
print("\nPORTFOLIO PARITY: PASS  (simulate_portfolio == validated overlay)" if ok else "\nPORTFOLIO PARITY: FAIL")
sys.exit(0 if ok else 1)
