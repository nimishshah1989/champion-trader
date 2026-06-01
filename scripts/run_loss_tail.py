"""Diagnose WHERE the loss comes from on the ladder+regime config.

Thesis: avgLossR -1.40 (not -1.0) => stops are gapping through. If true, the
loss tail (trades worse than -1.5R / -2R) is gap-downs, and the highest-leverage
fix is avoiding overnight gap risk (earnings blackout / quality filter), not a
different exit. Print the loss distribution + the worst offenders (symbol+dates).
"""
import sqlite3
import sys
from datetime import date

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars  # noqa: E402
from backend.engine.fills import DEFAULT_SLIPPAGE  # noqa: E402
from backend.engine.precompute import precompute_features  # noqa: E402
from backend.engine.regime import load_regime  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)

regime_map, _ = load_regime(CACHE, "NIFTY 500")
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done order by symbol")]

trades = []
for s in symbols:
    bars = load_bars(con, s)
    if len(bars) < 200:
        continue
    df = precompute_features(bars)
    trades += _fast_simulate(s, bars, df, exit_mode="ladder", target_r=2.0, chandelier_mult=3.0,
                             slippage=DEFAULT_SLIPPAGE, min_trp=2.0, start_date=START,
                             use_regime=True, regime_map=regime_map)
con.close()

# gross R per trade (synth exit already encodes blended ladder R)
rec = [(float((t.exit - t.entry) / t.stopdist), t) for t in trades]
rs = [r for r, _ in rec]
losers = sorted((x for x in rec if x[0] <= 0), key=lambda x: x[0])
winners = [r for r in rs if r > 0]

print(f"ladder + regime: {len(rs)} trades  (gross R, pre-cost)\n")
print(f"  wins   : {len(winners):>4} ({len(winners)/len(rs):.0%})   avg +{sum(winners)/len(winners):.2f}R" if winners else "")
nloss = len(losers)
print(f"  losses : {nloss:>4} ({nloss/len(rs):.0%})   avg {sum(r for r,_ in losers)/nloss:.2f}R\n")

print("Loss-tail concentration (this is the gap problem if the deep buckets are full):")
for thr in [-1.0, -1.25, -1.5, -2.0, -3.0]:
    n = sum(1 for r, _ in losers if r <= thr)
    bled = sum((r + 1.0) for r, _ in losers if r <= thr)   # R lost BEYOND a clean -1R stop
    print(f"  <= {thr:>5.2f}R : {n:>4} trades ({n/len(rs):>4.0%})   excess-vs-1R: {bled:>7.1f}R")

excess = sum(min(0.0, r + 1.0) for r, _ in losers)         # total R bled past a clean -1R
print(f"\n  TOTAL R bled past a clean -1R stop (gap damage): {excess:.1f}R "
      f"= {excess/len(rs):+.3f}R per trade of lost expectancy")

print("\nWorst 12 losers (gap-downs through the stop):")
for r, t in losers[:12]:
    print(f"  {t.symbol:14} {t.entry_date} -> {t.exit_date}  {r:>6.2f}R")
