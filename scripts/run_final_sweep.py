"""Final combination sweep — all three fixes together.

Close-based stops are already baked into backtest_fast.py. This script
sweeps chandelier mult × regime SMA speed to find the best combination,
and also tests the ladder with the faster regime.

All runs: RPT 0.5%, after costs, 2016+.
"""
import sqlite3
import sys
import time
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars, run_universe_backtest  # noqa: E402
from backend.engine.backtest import replay_trades  # noqa: E402
from backend.engine.fills import DEFAULT_SLIPPAGE  # noqa: E402
from backend.engine.precompute import precompute_features  # noqa: E402
from backend.engine.regime import load_regime  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)


def run_custom(exit_mode, chandelier_mult, sma_w, slope_lb):
    regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=sma_w, slope_lb=slope_lb)
    con = sqlite3.connect(CACHE)
    symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
    raw = []
    for s in symbols:
        bs = load_bars(con, s)
        if len(bs) < 200:
            continue
        df = precompute_features(bs)
        raw += _fast_simulate(s, bs, df, exit_mode=exit_mode, target_r=2.0,
                              chandelier_mult=chandelier_mult, slippage=DEFAULT_SLIPPAGE,
                              min_trp=2.0, start_date=START,
                              use_regime=True, regime_map=regime_map)
    con.close()
    return replay_trades(raw, starting_capital=Decimal("1000000"), rpt_pct=0.5)


print("Final combination sweep  (close-based stops, RPT 0.5%, after costs, 2016-2026)\n")
hdr = f"{'config':42}{'trades':>7}{'win':>7}{'avgWinR':>9}{'avgLossR':>9}{'expR':>8}{'SQN':>7}{'top5%':>7}{'finalEq':>13}"
print(hdr)
print("-" * len(hdr))

combos = [
    # baseline reference
    ("chandelier 3x  SMA150/20 [baseline]",   "chandelier", 3.0, 150, 20),
    # faster regime only
    ("chandelier 3x  SMA50/5",                "chandelier", 3.0,  50,  5),
    # wider trail only
    ("chandelier 5x  SMA150/20",              "chandelier", 5.0, 150, 20),
    # both together
    ("chandelier 5x  SMA50/5  ← key combo",  "chandelier", 5.0,  50,  5),
    # ladder variants
    ("ladder        SMA150/20 [baseline]",    "ladder",     3.0, 150, 20),
    ("ladder        SMA50/5",                 "ladder",     3.0,  50,  5),
]

for label, mode, mult, sma, slb in combos:
    t = time.time()
    res = run_custom(mode, mult, sma, slb)
    rs = res.r_multiples
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    aw = sum(wins)/len(wins) if wins else 0
    al = sum(losses)/len(losses) if losses else 0
    top5 = sum(sorted(wins, reverse=True)[:5]) / sum(wins) if wins else 0
    print(f"{label:42}{res.num_trades:>7}{res.win_rate:>7.1%}{aw:>9.2f}{al:>9.2f}"
          f"{res.expectancy:>+8.3f}{res.sqn:>7.2f}{top5:>7.0%}"
          f"{res.final_equity:>13,.0f}  ({time.time()-t:.0f}s)")

print(f"\nBenchmark: NIFTY 500 buy-and-hold ~13.4%/yr, Calmar ~0.30")
print("SQN interpretation: >1.0 good, >1.5 excellent, >2.0 superb (Van Tharp)")
print("NOTE: finalEq is sequential replay (not concurrent portfolio) — use SQN/expR as truth.")
