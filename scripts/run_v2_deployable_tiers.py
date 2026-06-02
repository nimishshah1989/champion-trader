"""DEPLOYABLE-TIER v2 — what's left after you strip the names you can't trade at size?

Runs the FULL validated v2 portfolio overlay (RPT 0.35%, max 15, bear-sizing 0.25x,
15% DD breaker, idle cash 6.5%, momentum-rank same-day selection, NSE costs, tiered
slippage) restricted to a rising liquidity FLOOR. A trade is kept only if the stock's
entry-time turnover (median close*volume over the prior 60 bars) >= the floor — i.e.
it simulates "my tradeable universe is names >= Rs X cr/day at the time."

Tier 0 = full universe (should reproduce the headline v2: ~26.5% CAGR / 14.8% DD /
1.79 Calmar / 2.34 TEST Calmar / 19.5% ex-2021). Higher floors = the honest,
fillable, less survivorship-prone edge.

Caveat: post-filtering a slow-moving turnover floor is a close approximation of an
in-engine universe gate (it can't re-derive a later entry a skipped name might have
taken) — but it errs conservative and the error is small for a 60-day median.
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
from backend.engine.backtest_fast import _fast_simulate, load_bars   # noqa: E402
from backend.engine.costs import CostModel                           # noqa: E402
from backend.engine.precompute import precompute_features            # noqa: E402
from backend.engine.regime import load_regime                        # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
START_CAP = Decimal("100000")
DAILY_YIELD = (1 + 0.065) ** (1 / 252) - 1
RPT = 0.35
CR = 1e7
cm = CostModel()
TIERS = [0, 1, 5, 15, 25, 50]   # Rs cr/day turnover floors


def slip(a):
    return Decimal("0.0010") if a >= 15 else Decimal("0.0025") if a >= 5 else Decimal("0.0050") if a >= 1 else Decimal("0.0100")


regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
close_lookup, score_lookup = {}, {}
trades_turn = []   # (RawTrade, entry_turnover_cr)
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    close_lookup[s] = {b.date: b.close for b in bs}
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    sl = slip(median(tnv) / CR if tnv else 0)
    # momentum score for same-day selection (identical to the validated v2 harness)
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
    idx_of = {b.date: i for i, b in enumerate(bs)}
    tr = _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                        slippage=sl, min_trp=2.0, start_date=START, use_regime=False,
                        skip_circuit_locked=True, vol_breakout_k=2.0)
    for t in tr:
        i = idx_of[t.entry_date]
        win = [float(bs[k].close) * bs[k].volume for k in range(max(0, i - 60), i)]
        turn_cr = (median(win) / CR) if win else (median(tnv) / CR if tnv else 0)
        trades_turn.append((t, turn_cr))
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()

FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}
TRAIN = [d for d in FULL if d.year < 2021]
TEST = [d for d in FULL if d.year >= 2021]


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(trades, cal, *, dd_halt=0.15, bear_frac=0.25, max_pos=15):
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


def yearly(curve):
    end = OrderedDict()
    for d, v in curve:
        end[d.year] = v
    res = OrderedDict(); prev = float(START_CAP)
    for y, v in end.items():
        res[y] = v / prev - 1; prev = v
    return res


def ex2021_cagr(curve):
    ys = yearly(curve); span = (FULL[-1] - FULL[0]).days / 365.25 - 1.0
    fac = 1.0
    for y, r in ys.items():
        if y != 2021:
            fac *= (1 + r)
    return fac ** (1 / span) - 1


# benchmark
_f = float(START_CAP) / idx_close[FULL[0]]
bench = met([(d, idx_close[d] * _f) for d in FULL], FULL)
bench_ex = ex2021_cagr([(d, idx_close[d] * _f) for d in FULL])

print(f"v2 portfolio by liquidity FLOOR  (RPT {RPT}% | full v2 trades = {len(trades_turn)})\n")
print(f"{'floor':>10}{'#trades':>9}{'final Rs':>12}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}{'TESTcal':>9}{'ex2021':>8}")
print("-" * 88)
curves = OrderedDict()
for T in TIERS:
    sub = [t for t, turn in trades_turn if turn >= T]
    cf = portfolio(sub, FULL)
    cagr, mdd, cal_, shp = met(cf, FULL)
    _, _, tcal, _ = met(portfolio(sub, TEST), TEST)
    exc = ex2021_cagr(cf)
    label = "FULL" if T == 0 else f">={T}cr"
    curves[label] = cf
    print(f"{label:>10}{len(sub):>9}{cf[-1][1]:>12,.0f}{cagr:>8.1%}{mdd:>8.1%}{cal_:>8.2f}{shp:>8.2f}{tcal:>9.2f}{exc:>8.1%}")
print("-" * 88)
print(f"{'NIFTY500':>10}{'-':>9}{(idx_close[FULL[-1]]*_f):>12,.0f}{bench[0]:>8.1%}{bench[1]:>8.1%}{bench[2]:>8.2f}{bench[3]:>8.2f}{'-':>9}{bench_ex:>8.1%}")
print("\nfloor = min entry-time turnover (Rs cr/day). FULL should reproduce the headline v2.")

# ---- per-year returns by liquidity floor ----
labels = list(curves.keys())
bench_curve = [(d, idx_close[d] * _f) for d in FULL]
yt = {lab: yearly(curves[lab]) for lab in labels}
yb = yearly(bench_curve)
bull = defaultdict(lambda: [0, 0])
for d in FULL:
    bull[d.year][0 if regime_map.get(d, False) else 1] += 1
hdr = f"{'year':>6}" + "".join(f"{lab:>8}" for lab in labels) + f"{'NIFTY500':>10}{'bull':>6}"
print("\nPER-YEAR RETURNS by liquidity floor:")
print(hdr); print("-" * len(hdr))
for y in sorted(yb.keys()):
    bd = bull[y]; pct = bd[0] / (bd[0] + bd[1]) if (bd[0] + bd[1]) else 0
    row = f"{y:>6}" + "".join(f"{yt[lab].get(y, 0):>8.1%}" for lab in labels) + f"{yb.get(y, 0):>10.1%}{pct:>6.0%}"
    print(row)
print("-" * len(hdr))
cagrs = {lab: met(curves[lab], FULL)[0] for lab in labels}
print(f"{'CAGR':>6}" + "".join(f"{cagrs[lab]:>8.1%}" for lab in labels) + f"{bench[0]:>10.1%}{'':>6}")
print(f"{'ex21':>6}" + "".join(f"{ex2021_cagr(curves[lab]):>8.1%}" for lab in labels) + f"{bench_ex:>10.1%}{'':>6}")
