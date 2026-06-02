"""The decision that defines the system: hard intraday stop vs EOD close stop.

Trade-off:
  - intraday stop ("target"): a resting -1R stop order. Caps losses near -1R,
    but may stop out on noise before the target (the 78% premature finding).
  - close stop ("target_close"): only exits if the CLOSE is below -1R. Avoids
    wick exits -> higher win rate, but the close is often well below -1R -> the
    average loss balloons to ~-1.5R.

The user's target profile is ~53-57% win, +2-2.5R wins, losers at -1 to -1.2R.
Whichever stop gives the best expectancy AND keeps losers tight wins.
Reported: win%, avgWin, avgLoss, %losers worse than -1.2R, expectancy, SQN, top5%.
SMA50/5 regime, RPT 0.5%, after costs, 2016+.
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


def run(exit_mode, target_r):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode=exit_mode, target_r=target_r,
                              chandelier_mult=3.0, slippage=DEFAULT_SLIPPAGE,
                              min_trp=2.0, start_date=START, use_regime=True, regime_map=regime_map)
    return replay_trades(raw, starting_capital=Decimal("1000000"), rpt_pct=0.5)


print("\nHARD intraday stop vs EOD close stop  (SMA50/5 regime, 2016-2026)\n")
hdr = (f"{'config':28}{'trades':>7}{'win':>7}{'avgWin':>8}{'avgLoss':>8}"
       f"{'loss<-1.2':>10}{'expR':>8}{'SQN':>7}{'top5%':>7}")
print(hdr); print("-" * len(hdr))

for tr in [2.0, 2.5, 3.0]:
    for mode, tag in [("target", "intraday-stop"), ("target_close", "close-stop  ")]:
        res = run(mode, tr)
        rs = res.r_multiples
        wins = [r for r in rs if r > 0]; losses = [r for r in rs if r <= 0]
        aw = sum(wins)/len(wins) if wins else 0
        al = sum(losses)/len(losses) if losses else 0
        bad = sum(1 for r in losses if r < -1.2) / len(losses) if losses else 0
        top5 = sum(sorted(wins, reverse=True)[:5])/sum(wins) if wins else 0
        print(f"{f'{tr}R {tag}':28}{res.num_trades:>7}{res.win_rate:>7.1%}{aw:>8.2f}{al:>8.2f}"
              f"{bad:>10.0%}{res.expectancy:>+8.3f}{res.sqn:>7.2f}{top5:>7.0%}")
    print()

print("loss<-1.2 = fraction of losing trades worse than -1.2R (gap/close damage).")
print("Target profile: ~50-55% win, losers tight (-1 to -1.2R), high SQN, low top5%.")
