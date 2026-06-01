"""Broad-universe backtest over the local Atlas cache — the first statistically
meaningful, after-cost result on the full ~1,310-name universe (2007-2026).
Still v1 exit (stop + fixed 2R); ride-winners/trailing + calibration come next.
"""
import sys
import time
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import run_universe_backtest  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"

t = time.time()
res, used = run_universe_backtest(CACHE, starting_capital=Decimal("1000000"), rpt_pct=0.5, target_r=2.0)
dt = time.time() - t

print(f"\n=== BROAD UNIVERSE BACKTEST  ({used} symbols, 2007-2026; honest costs+slippage; v1 stop+2R exit) ===")
print(f"  ran in        : {dt:.0f}s")
print(f"  trades        : {res.num_trades}")
print(f"  win rate      : {res.win_rate:.1%}")
print(f"  expectancy    : {res.expectancy:+.3f} R")
print(f"  avg R:R (ARR) : {res.arr:.2f}")
print(f"  SQN           : {res.sqn:.2f}")
print(f"  max drawdown  : {res.max_drawdown:.1%}")
print(f"  Calmar        : {res.calmar:.2f}")
print(f"  final equity  : Rs {res.final_equity:,.0f}  (from 10,00,000)")
