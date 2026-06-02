"""Sample real-data backtest — a first end-to-end result on live Kite data.

NOT the Baseline Card (that needs the full point-in-time NIFTY-500 universe +
walk-forward + RS/sector). This is a sanity run of the honest engine (real costs
+ slippage, gap-aware fills) on a handful of large-caps, with the v1 exit
(stop + fixed 2R target). Run from the repo root.
"""
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")

from backend.engine.backtest import run_backtest          # noqa: E402
from backend.engine.kite_data import KiteHistoricalAdapter  # noqa: E402
from backend.engine.production_signal import production_signal  # noqa: E402

env = {}
for line in open("/home/user/champion-trader/.env"):
    s = line.strip()
    if "=" in s and not s.startswith("#"):
        k, v = s.split("=", 1)
        env[k] = v

SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "ITC",
           "LT", "AXISBANK", "BHARTIARTL", "MARUTI", "SUNPHARMA", "TITAN", "ASIANPAINT"]

ad = KiteHistoricalAdapter(env["KITE_API_KEY"], env["KITE_ACCESS_TOKEN"])
end = date.today()
start = end - timedelta(days=365 * 4)

data = {}
for s in SYMBOLS:
    try:
        bars = ad.daily_bars(s, start, end, as_of=end)
        if len(bars) >= 200:
            data[s] = bars
    except Exception as exc:
        print(f"  {s}: FAILED {exc}")
print(f"loaded {len(data)}/{len(SYMBOLS)} symbols, ~{sum(len(b) for b in data.values())} bars")

res = run_backtest(data, production_signal(), starting_capital=Decimal("1000000"),
                   rpt_pct=0.5, target_r=2.0)

print("\n=== SAMPLE BACKTEST  (real Kite data; honest costs + slippage; v1 stop+2R exit) ===")
print(f"  trades        : {res.num_trades}")
print(f"  win rate      : {res.win_rate:.1%}")
print(f"  expectancy    : {res.expectancy:+.3f} R")
print(f"  avg R:R (ARR) : {res.arr:.2f}")
print(f"  SQN           : {res.sqn:.2f}")
print(f"  max drawdown  : {res.max_drawdown:.1%}")
print(f"  Calmar        : {res.calmar:.2f}")
print(f"  final equity  : Rs {res.final_equity:,.0f}  (from 10,00,000)")
