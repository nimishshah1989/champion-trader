"""TRACK 2: principled momentum-rank selection of same-day candidates.

Track 1 showed that when capacity-bound (~7 slots), WHICH competing same-day
breakout we take is currently arbitrary (alphabetical) -> a ~5% CAGR noise band.
Fix: rank same-day candidates by the NSE-index risk-adjusted momentum score
  score = 0.5 * (6m return / 1yr daily-vol) + 0.5 * (12m return / 1yr daily-vol)
measured at the SIGNAL bar (no look-ahead), and take the strongest first.

A/B on the HONEST baseline (tiered slippage + circuit-skip):
  ARBITRARY (median of random orderings)  vs  MOMENTUM-RANK (deterministic)
  + REVERSE-RANK (weakest first) as a sanity check: if momentum carries info,
    reverse must do WORSE than arbitrary.
"""
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from math import sqrt
from statistics import median

import numpy as np

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars  # noqa: E402
from backend.engine.costs import CostModel                          # noqa: E402
from backend.engine.precompute import precompute_features           # noqa: E402
from backend.engine.regime import load_regime                       # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
START_CAP = Decimal("100000")
DAILY_YIELD = (1 + 0.065) ** (1 / 252) - 1
cm = CostModel()


def slip_for_adt(adt_cr):
    if adt_cr >= 15:
        return Decimal("0.0010")
    if adt_cr >= 5:
        return Decimal("0.0025")
    if adt_cr >= 1:
        return Decimal("0.0050")
    return Decimal("0.0100")


regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
all_bars, close_lookup, adt, score_lookup = {}, {}, {}, {}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    all_bars[s] = (bs, df)
    close_lookup[s] = {b.date: b.close for b in bs}
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    adt[s] = median(tnv) / 1e7 if tnv else 0
    # risk-adjusted momentum score per bar (raw; ranking-equivalent to the NSE z-score)
    c = df["close"].astype(float).to_numpy()
    ret126 = np.full(len(c), np.nan); ret252 = np.full(len(c), np.nan)
    ret126[126:] = c[126:] / c[:-126] - 1
    ret252[252:] = c[252:] / c[:-252] - 1
    dret = np.diff(c) / c[:-1]
    vol = np.full(len(c), np.nan)
    for k in range(252, len(c)):
        sd = dret[k-252:k].std()
        vol[k] = sd if sd > 0 else np.nan
    score = 0.5 * (ret126 / vol) + 0.5 * (ret252 / vol)
    # map a candidate entry_date -> score at the PRIOR (signal) bar (no look-ahead)
    for k in range(len(bs) - 1):
        sc = score[k]
        if sc == sc:
            score_lookup[(s, bs[k + 1].date)] = float(sc)
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}
TRAIN = [d for d in FULL if d.year < 2021]
TEST = [d for d in FULL if d.year >= 2021]

# honest trade set (tiered slippage + circuit-skip)
trades = []
for s, (bs, df) in all_bars.items():
    trades += _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                             slippage=slip_for_adt(adt[s]), min_trp=2.0, start_date=START,
                             use_regime=False, regime_map=regime_map, skip_circuit_locked=True)
cov = sum(1 for t in trades if (t.symbol, t.entry_date) in score_lookup) / len(trades)
print(f"{len(trades)} honest trades; momentum score available for {cov:.0%} of them\n")


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(cal, *, order, rpt_pct=0.25, bear_frac=0.25, dd_halt=0.15, max_pos=15, seed=0):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    for d in eo:
        if order == "rank":
            eo[d].sort(key=lambda t: score_lookup.get((t.symbol, t.entry_date), -1e9), reverse=True)
        elif order == "reverse":
            eo[d].sort(key=lambda t: score_lookup.get((t.symbol, t.entry_date), 1e9))
        elif order == "shuffle":
            import random
            random.Random(seed + hash(d) % 1000).shuffle(eo[d])
    rpt = Decimal(str(rpt_pct)); resume = dd_halt * 0.5
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
        curve.append(float(eq))
    return curve


def met(curve, cal):
    yrs = (cal[-1] - cal[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / yrs) - 1
    pk = curve[0]; mdd = 0
    for v in curve:
        pk = max(pk, v); mdd = max(mdd, (pk - v) / pk)
    rets = [curve[i] / curve[i-1] - 1 for i in range(1, len(curve))]
    m = sum(rets) / len(rets); var = sum((r-m)**2 for r in rets) / len(rets)
    return cagr, mdd, (cagr / mdd if mdd else 0), (m / sqrt(var) * sqrt(252) if var > 0 else 0)


print(f"{'selection':22}{'window':14}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}")
print("-" * 68)
# arbitrary = median of 8 random orderings (the noise-band centre)
for name, cal in [("TRAIN 16-20", TRAIN), ("TEST 21-26", TEST), ("FULL 16-26", FULL)]:
    cs = sorted(met(portfolio(cal, order="shuffle", seed=sd), cal)[0] for sd in range(8))
    cl = sorted(met(portfolio(cal, order="shuffle", seed=sd), cal)[2] for sd in range(8))
    print(f"{'ARBITRARY (median)':22}{name:14}{cs[4]:>8.1%}{'':>8}{cl[4]:>8.2f}{'':>8}")
print("-" * 68)
for label, order in [("MOMENTUM-RANK", "rank"), ("REVERSE-RANK (sanity)", "reverse")]:
    for name, cal in [("TRAIN 16-20", TRAIN), ("TEST 21-26", TEST), ("FULL 16-26", FULL)]:
        m = met(portfolio(cal, order=order), cal)
        print(f"{label:22}{name:14}{m[0]:>8.1%}{m[1]:>8.1%}{m[2]:>8.2f}{m[3]:>8.2f}")
    print("-" * 68)
print("WANT: MOMENTUM-RANK > ARBITRARY > REVERSE-RANK (on TEST). If rank>reverse, the")
print("momentum signal carries selection info; rank is also deterministic (no noise band).")
