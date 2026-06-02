"""Broad-universe backtest over the local Atlas cache, comparing exit policies.

RPT sizing IS active: replay_trades sizes each trade as
    shares = floor( (current_equity * RPT%) / risk_per_share )
where risk_per_share = entry - stop (the TRP value). Equity compounds; real NSE
costs are charged on the sized position; R = net_pnl / (shares * risk_per_share).
"""
import sys
import time
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import run_universe_backtest  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
RPT = 0.5

print("Universe backtest  (RPT %.2f%% of equity per trade, compounding, after NSE costs+slippage)\n" % RPT)
print(f"{'exit policy':14}{'trades':>7}{'win':>7}{'avgWinR':>9}{'avgLossR':>9}{'expR':>8}{'SQN':>7}{'maxDD':>7}{'Calmar':>8}{'finalEq':>13}")
for mode in ["target", "chandelier"]:
    t = time.time()
    res, used = run_universe_backtest(CACHE, exit_mode=mode, rpt_pct=RPT)
    dt = time.time() - t
    rs = res.r_multiples
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    print(f"{mode:14}{res.num_trades:>7}{res.win_rate:>7.1%}{avg_win:>9.2f}{avg_loss:>9.2f}"
          f"{res.expectancy:>+8.3f}{res.sqn:>7.2f}{res.max_drawdown:>7.1%}{res.calmar:>8.2f}"
          f"{res.final_equity:>13,.0f}   ({dt:.0f}s, {used} syms)")
