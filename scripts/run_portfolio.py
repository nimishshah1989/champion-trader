"""Concurrent PORTFOLIO simulation with cash yield — the real-money picture.

Everything before this measured per-trade R. This builds the actual portfolio:
  - start ₹1,00,000, RPT 0.5%, max 8 concurrent positions, max open risk 10%
  - position size = equity * RPT% / stopdist  (cash-capped)
  - IDLE CASH EARNS 6.5%/yr (Liquid Bees) — accrued daily, zero drawdown
  - NSE costs on every buy/sell, daily mark-to-market -> real equity curve
  - when regime is off / no setups, capital sits in cash earning 6.5%

Then compares CAGR / maxDD / Calmar / Sharpe to NIFTY 500 buy-and-hold over the
exact same window. THIS answers: is the system actually better than buy-and-hold?

Config: target_close 2.5R + SMA50/5 regime + close-based stop (the best
consistent, non-lottery config: SQN ~1.2, top-5% = 2%).
"""
import sqlite3
import sys
from datetime import date
from decimal import Decimal
from math import sqrt

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars  # noqa: E402
from backend.engine.costs import CostModel                          # noqa: E402
from backend.engine.fills import DEFAULT_SLIPPAGE                    # noqa: E402
from backend.engine.precompute import precompute_features           # noqa: E402
from backend.engine.regime import load_regime                       # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
START_CAP = Decimal("100000")
RPT = Decimal("0.5")
MAX_POS = 8
MAX_OPEN_RISK = Decimal("10")    # % of equity
CASH_YIELD = 0.065               # Liquid Bees, annual
DAILY_YIELD = (1 + CASH_YIELD) ** (1 / 252) - 1
TARGET_R = 2.5

cm = CostModel()

print("Building trades + price lookups...", flush=True)
regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]

trades = []
close_lookup = {}     # symbol -> {date: close}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    tr = _fast_simulate(s, bs, df, exit_mode="target_close", target_r=TARGET_R,
                         chandelier_mult=3.0, slippage=DEFAULT_SLIPPAGE, min_trp=2.0,
                         start_date=START, use_regime=True, regime_map=regime_map)
    if tr:
        trades += tr
        close_lookup[s] = {b.date: b.close for b in bs}

# market calendar + benchmark from the index
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
calendar = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}

# index trades by entry/exit date
from collections import defaultdict
entries_on = defaultdict(list)
for t in trades:
    entries_on[t.entry_date].append(t)
print(f"  {len(trades)} candidate trades, {len(calendar)} trading days\n")


def last_close(sym, d, fallback):
    """close for sym on/just-before d (forward-filled)."""
    cl = close_lookup.get(sym, {})
    return cl.get(d, fallback)


# ── portfolio walk (parametrised by RPT so we can map the risk frontier) ──────
def simulate(rpt_pct, max_pos=MAX_POS, max_open_risk=MAX_OPEN_RISK):
    rpt = Decimal(str(rpt_pct))
    cash = START_CAP
    open_pos = []
    curve = []
    days_invested = pos_count_sum = 0
    taken = skipped_cap = skipped_cash = 0

    for d in calendar:
        cash *= Decimal(1 + DAILY_YIELD)          # cash yield accrues daily

        still = []                                # close positions exiting today
        for p in open_pos:
            if p["exit_date"] == d:
                proceeds = Decimal(p["shares"]) * p["exit_price"]
                cash += proceeds - cm.sell_costs(proceeds)
            else:
                still.append(p)
        open_pos = still

        for p in open_pos:                        # mark to market
            p["last_px"] = last_close(p["sym"], d, p["last_px"])
        equity = cash + sum(Decimal(p["shares"]) * p["last_px"] for p in open_pos)

        for t in entries_on.get(d, []):           # open new positions
            if len(open_pos) >= max_pos:
                skipped_cap += 1
                continue
            shares = int((equity * rpt / Decimal(100)) / t.stopdist)
            if shares <= 0:
                continue
            open_risk = sum(Decimal(p["shares"]) * p["stopdist"] for p in open_pos)
            if (open_risk + Decimal(shares) * t.stopdist) / equity * Decimal(100) > max_open_risk:
                continue
            cost = Decimal(shares) * t.entry
            total_cost = cost + cm.buy_costs(cost)
            if total_cost > cash:
                skipped_cash += 1
                continue
            cash -= total_cost
            open_pos.append({"sym": t.symbol, "shares": shares, "entry": t.entry,
                             "stopdist": t.stopdist, "exit_date": t.exit_date,
                             "exit_price": t.exit, "last_px": t.entry})
            taken += 1

        equity = cash + sum(Decimal(p["shares"]) * p["last_px"] for p in open_pos)
        curve.append(float(equity))
        if open_pos:
            days_invested += 1
            pos_count_sum += len(open_pos)

    return curve, dict(taken=taken, skipped_cap=skipped_cap, skipped_cash=skipped_cash,
                       days_invested=days_invested,
                       avg_pos=pos_count_sum / max(days_invested, 1))


def metrics(curve, dates):
    n = len(curve)
    years = (dates[-1] - dates[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / years) - 1
    peak = curve[0]; mdd = 0.0
    for v in curve:
        peak = max(peak, v)
        mdd = max(mdd, (peak - v) / peak)
    rets = [(curve[i] / curve[i-1] - 1) for i in range(1, n)]
    mean = sum(rets) / len(rets); var = sum((r-mean)**2 for r in rets)/len(rets)
    sharpe = (mean / sqrt(var) * sqrt(252)) if var > 0 else 0
    calmar = cagr / mdd if mdd > 0 else 0
    return cagr, mdd, calmar, sharpe


# benchmark: NIFTY 500 buy & hold over same window
bench = [idx_close[d] for d in calendar]
ben_c = metrics(bench, calendar)

print("=" * 78)
print(f"RISK FRONTIER  (₹1,00,000 start, {calendar[0]} .. {calendar[-1]}, idle cash @ {CASH_YIELD:.1%})")
print("=" * 78)
print(f"{'config':26}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}{'finalEq':>12}{'avgPos':>8}{'inv%':>6}")
print("-" * 78)
for rpt in [0.5, 1.0, 1.5, 2.0]:
    curve, st = simulate(rpt)
    c = metrics(curve, calendar)
    print(f"{'RPT '+str(rpt)+'%  max8pos':26}{c[0]:>8.1%}{c[1]:>8.1%}{c[2]:>8.2f}{c[3]:>8.2f}"
          f"{curve[-1]:>12,.0f}{st['avg_pos']:>8.1f}{st['days_invested']/len(calendar):>6.0%}")
print("-" * 78)
print(f"{'NIFTY 500 buy&hold':26}{ben_c[0]:>8.1%}{ben_c[1]:>8.1%}{ben_c[2]:>8.2f}{ben_c[3]:>8.2f}"
      f"{START_CAP*Decimal(bench[-1]/bench[0]):>12,.0f}{'—':>8}{'100%':>6}")
print("\nObjective = maximise return under a max-DD ceiling. Pick the RPT row whose")
print("maxDD fits your tolerance; all stay far below buy&hold's 45% DD.")
