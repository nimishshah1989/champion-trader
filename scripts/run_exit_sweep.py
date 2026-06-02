"""Test the fat-tail hypothesis: are we cutting winners too short?

Same config (+regime, RPT 0.5%, 2016+), sweep the chandelier ATR multiple. If a
WIDER trail lifts avg-win-R / max-R / the count of 10R+ winners and improves
expectancy, our exit was amputating the trend-following edge.
"""
import sys
import time
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import run_universe_backtest  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)

print("Exit-width sweep  (+regime, RPT 0.5%, chandelier trail, 2016-2026)\n")
print(f"{'ATR x':>6}{'trades':>7}{'win':>7}{'avgWinR':>9}{'maxR':>7}{'#>=10R':>7}{'expR':>8}{'SQN':>7}{'maxDD':>7}{'Calmar':>8}{'finalEq':>13}")
for mult in [2.0, 3.0, 5.0, 8.0, 12.0]:
    t = time.time()
    res, _ = run_universe_backtest(CACHE, exit_mode="chandelier", chandelier_mult=mult,
                                   use_regime=True, start_date=START)
    rs = res.r_multiples
    wins = [r for r in rs if r > 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    mx = max(rs) if rs else 0.0
    big = sum(1 for r in rs if r >= 10)
    print(f"{mult:>6.0f}{res.num_trades:>7}{res.win_rate:>7.1%}{aw:>9.2f}{mx:>7.1f}{big:>7}"
          f"{res.expectancy:>+8.3f}{res.sqn:>7.2f}{res.max_drawdown:>7.1%}{res.calmar:>8.2f}"
          f"{res.final_equity:>13,.0f}  ({time.time()-t:.0f}s)")
