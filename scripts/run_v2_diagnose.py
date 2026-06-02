"""Why does v2 (breakout-volume filter) only beat v1 + market from 2022?

Take EVERY breakout trade (no volume filter = v1's universe), tag each with its
breakout-day volume ratio (vol / 50d-avg) and its realized R, then split by era:
  - Does the >=2x volume signal DISCRIMINATE winners from losers more post-2022?
  - Did breakouts in general just get better post-2022 (a market-regime shift)?
Per-trade R controls for "fewer trades" -- it isolates signal quality, not luck.
"""
import sqlite3
import sys
import warnings
from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import median, mean

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars  # noqa: E402
from backend.engine.precompute import precompute_features           # noqa: E402
from backend.engine.regime import load_regime                       # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)


def slip(a):
    return Decimal("0.0010") if a >= 15 else Decimal("0.0025") if a >= 5 else Decimal("0.0050") if a >= 1 else Decimal("0.0100")


regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
recs = []   # (entry_year, R, vol_ratio)
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    adt = median(tnv) / 1e7 if tnv else 0
    vsma50 = df["vol_sma50"].to_numpy()
    idx_of = {b.date: i for i, b in enumerate(bs)}
    tr = _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                        slippage=slip(adt), min_trp=2.0, start_date=START, use_regime=False,
                        regime_map=regime_map, skip_circuit_locked=True)
    for t in tr:
        i = idx_of[t.entry_date]
        v50 = vsma50[i]
        if not (v50 == v50) or v50 <= 0:
            continue
        ratio = bs[i].volume / v50
        R = float((t.exit - t.entry) / t.stopdist)
        recs.append((t.entry_date.year, R, ratio))
con.close()
print(f"{len(recs)} breakout trades tagged with breakout-day volume ratio\n")


def stats(rows):
    n = len(rows)
    if n == 0:
        return (0, 0, 0, 0)
    rs = [r for _, r, _ in rows]
    return (n, sum(1 for r in rs if r > 0) / n, mean(rs), sum(rs))


ERAS = [("2016-2021", lambda y: y <= 2021), ("2022-2026", lambda y: y >= 2022)]
print("BASE RATE (all breakouts, regardless of volume) -- did breakouts just get better?")
print(f"{'era':12}{'n':>5}{'win%':>7}{'meanR':>8}{'sumR':>8}")
for name, f in ERAS:
    n, w, mr, sr = stats([r for r in recs if f(r[0])])
    print(f"{name:12}{n:>5}{w:>7.0%}{mr:>+8.2f}{sr:>+8.0f}")

print("\nVOLUME DISCRIMINATION -- high(>=2x) vs low(<2x) breakout volume, by era:")
print(f"{'era':12}{'bucket':>9}{'n':>5}{'win%':>7}{'meanR':>8}{'sumR':>8}")
for name, f in ERAS:
    era = [r for r in recs if f(r[0])]
    lo = [r for r in era if r[2] < 2.0]
    hi = [r for r in era if r[2] >= 2.0]
    nl, wl, ml, sl = stats(lo)
    nh, wh, mh, sh = stats(hi)
    print(f"{name:12}{'low <2x':>9}{nl:>5}{wl:>7.0%}{ml:>+8.2f}{sl:>+8.0f}")
    print(f"{name:12}{'high>=2x':>9}{nh:>5}{wh:>7.0%}{mh:>+8.2f}{sh:>+8.0f}")
    print(f"{'':12}{'-> edge':>9}{'':>5}{(wh-wl):>+7.0%}{(mh-ml):>+8.2f}  (high minus low)")

print("\nPer-year: meanR of high(>=2x) vs low(<2x) volume breakouts (when did the gap open?)")
print(f"{'year':>6}{'n_lo':>6}{'meanR_lo':>10}{'n_hi':>6}{'meanR_hi':>10}{'gap':>8}")
by_year = defaultdict(list)
for r in recs:
    by_year[r[0]].append(r)
for y in sorted(by_year):
    lo = [r for r in by_year[y] if r[2] < 2.0]
    hi = [r for r in by_year[y] if r[2] >= 2.0]
    ml = mean([r for _, r, _ in lo]) if lo else 0
    mh = mean([r for _, r, _ in hi]) if hi else 0
    print(f"{y:>6}{len(lo):>6}{ml:>+10.2f}{len(hi):>6}{mh:>+10.2f}{(mh-ml):>+8.2f}")
