"""Ablation study: add one edge-variable at a time and watch the marginal effect.

All runs: ride-winners (chandelier) exit, RPT 0.5%, NSE costs+slippage, 2016+
(where index data exists, for a fair comparison). We are LOOKING FOR which
variables carry the edge -- not forcing thresholds.
"""
import sys
import time
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import run_universe_backtest  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)

configs = [
    ("baseline (no filters)",   dict()),
    ("+ regime",                dict(use_regime=True)),
    ("+ regime +52wHigh",       dict(use_regime=True, use_52w=True, max_pct_52w=15.0)),
    ("+ regime +52w +RS",       dict(use_regime=True, use_52w=True, max_pct_52w=15.0, use_rs=True, rs_min=0.0)),
]

print("Ablation  (chandelier exit, RPT 0.5%, after costs, 2016-2026)\n")
print(f"{'config':24}{'trades':>7}{'win':>7}{'avgWinR':>9}{'avgLossR':>9}{'expR':>8}{'SQN':>7}{'maxDD':>7}{'Calmar':>8}{'finalEq':>13}")
for name, kw in configs:
    t = time.time()
    res, used = run_universe_backtest(CACHE, exit_mode="chandelier", start_date=START, **kw)
    dt = time.time() - t
    rs = res.r_multiples
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    print(f"{name:24}{res.num_trades:>7}{res.win_rate:>7.1%}{aw:>9.2f}{al:>9.2f}"
          f"{res.expectancy:>+8.3f}{res.sqn:>7.2f}{res.max_drawdown:>7.1%}{res.calmar:>8.2f}"
          f"{res.final_equity:>13,.0f}   ({dt:.0f}s)")
