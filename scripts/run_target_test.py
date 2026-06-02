"""The decisive test: does a fixed-target bracket capture the 52% hit_2R edge?

The IC study found the raw setups hit 2R-before-1R 52.3% of the time. The ladder
and chandelier exits ride past 2R and give it back. A clean fixed ~2-2.5R target
with a close-based 1R stop should realise that 52% win rate at high SQN (low
variance). Sweep the target and compare to the let-it-ride exits, all with the
faster SMA50/5 regime + close-based stops, RPT 0.5%, after costs, 2016+.
"""
import sqlite3
import sys
import time
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars  # noqa: E402
from backend.engine.backtest import replay_trades                   # noqa: E402
from backend.engine.fills import DEFAULT_SLIPPAGE                    # noqa: E402
from backend.engine.precompute import precompute_features           # noqa: E402
from backend.engine.regime import load_regime                       # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)

print("Preloading...", flush=True)
regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
all_bars = {}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) >= 200:
        all_bars[s] = (bs, precompute_features(bs))
con.close()


def run(exit_mode, target_r=2.0, chandelier_mult=3.0):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode=exit_mode, target_r=target_r,
                              chandelier_mult=chandelier_mult, slippage=DEFAULT_SLIPPAGE,
                              min_trp=2.0, start_date=START, use_regime=True, regime_map=regime_map)
    return replay_trades(raw, starting_capital=Decimal("1000000"), rpt_pct=0.5)


print("\nFixed-target bracket vs let-it-ride  (SMA50/5 regime, close-based stop, 2016-2026)\n")
hdr = f"{'config':30}{'trades':>7}{'win':>7}{'avgWinR':>9}{'avgLossR':>9}{'expR':>8}{'SQN':>7}{'top5%':>7}{'finalEq':>13}"
print(hdr); print("-" * len(hdr))

configs = [
    ("target 1.5R  (close stop)",  "target_close", 1.5, 3.0),
    ("target 2.0R  (close stop)",  "target_close", 2.0, 3.0),
    ("target 2.5R  (close stop)",  "target_close", 2.5, 3.0),
    ("target 3.0R  (close stop)",  "target_close", 3.0, 3.0),
    ("ladder        (ride)",       "ladder",       2.0, 3.0),
    ("chandelier 3x (ride)",       "chandelier",   2.0, 3.0),
]
for label, mode, tr, cm in configs:
    t = time.time()
    res = run(mode, tr, cm)
    rs = res.r_multiples
    wins = [r for r in rs if r > 0]; losses = [r for r in rs if r <= 0]
    aw = sum(wins)/len(wins) if wins else 0
    al = sum(losses)/len(losses) if losses else 0
    top5 = sum(sorted(wins, reverse=True)[:5])/sum(wins) if wins else 0
    print(f"{label:30}{res.num_trades:>7}{res.win_rate:>7.1%}{aw:>9.2f}{al:>9.2f}"
          f"{res.expectancy:>+8.3f}{res.sqn:>7.2f}{top5:>7.0%}{res.final_equity:>13,.0f}  ({time.time()-t:.0f}s)")

print("\nSQN: >1.5 excellent  >2.0 superb (Van Tharp).  Watch win% + top5% (consistency).")
