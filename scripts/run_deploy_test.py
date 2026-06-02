"""Test the user's thesis: stop gating on the INDEX, trade per-stock strength.

The index-regime gate keeps us in cash 53% of the time -> only ~22% deployed ->
11% blended return despite a ~27% edge on deployed capital. But strong stocks
trend regardless of the index ("there's always some instrument on the journey").
The stock is ALREADY required to be in a Stage-2 uptrend (above a rising long MA,
higher highs) and the per-trade stop caps each loss. So the index gate may be
redundant downside protection that's throttling deployment.

Compare, as full portfolios (1L, RPT 0.5%, max positions, cash @ 6.5%, costs):
  index-gate ON vs OFF, across fixed-target and let-it-run exits.
Watch deployment% + avgPos (the breadth lever) AND CAGR/maxDD/Calmar (does
trading the bear-market breakouts help or hurt after the stop protects each one).
"""
import sqlite3
import sys
import time
from collections import defaultdict
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
CASH_YIELD = 0.065
DAILY_YIELD = (1 + CASH_YIELD) ** (1 / 252) - 1
cm = CostModel()

print("Preloading...", flush=True)
regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
all_bars, close_lookup = {}, {}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    all_bars[s] = (bs, precompute_features(bs))
    close_lookup[s] = {b.date: b.close for b in bs}
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
calendar = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}


def gen_trades(exit_mode, target_r, use_regime, chandelier_mult=3.0):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode=exit_mode, target_r=target_r,
                              chandelier_mult=chandelier_mult, slippage=DEFAULT_SLIPPAGE,
                              min_trp=2.0, start_date=START, use_regime=use_regime,
                              regime_map=regime_map)
    return raw


def last_close(sym, d, fallback):
    return close_lookup.get(sym, {}).get(d, fallback)


def run_portfolio(trades, rpt_pct=0.5, max_pos=8, max_open_risk=Decimal("10")):
    entries_on = defaultdict(list)
    for t in trades:
        entries_on[t.entry_date].append(t)
    rpt = Decimal(str(rpt_pct))
    cash = START_CAP
    open_pos = []
    curve = []
    days_inv = pos_sum = 0
    for d in calendar:
        cash *= Decimal(1 + DAILY_YIELD)
        still = []
        for p in open_pos:
            if p["exit_date"] == d:
                proceeds = Decimal(p["shares"]) * p["exit_price"]
                cash += proceeds - cm.sell_costs(proceeds)
            else:
                still.append(p)
        open_pos = still
        for p in open_pos:
            p["last_px"] = last_close(p["sym"], d, p["last_px"])
        equity = cash + sum(Decimal(p["shares"]) * p["last_px"] for p in open_pos)
        for t in entries_on.get(d, []):
            if len(open_pos) >= max_pos:
                continue
            shares = int((equity * rpt / Decimal(100)) / t.stopdist)
            if shares <= 0:
                continue
            open_risk = sum(Decimal(p["shares"]) * p["stopdist"] for p in open_pos)
            if (open_risk + Decimal(shares) * t.stopdist) / equity * Decimal(100) > max_open_risk:
                continue
            cost = Decimal(shares) * t.entry
            total = cost + cm.buy_costs(cost)
            if total > cash:
                continue
            cash -= total
            open_pos.append({"sym": t.symbol, "shares": shares, "entry": t.entry,
                             "stopdist": t.stopdist, "exit_date": t.exit_date,
                             "exit_price": t.exit, "last_px": t.entry})
        equity = cash + sum(Decimal(p["shares"]) * p["last_px"] for p in open_pos)
        curve.append(float(equity))
        if open_pos:
            days_inv += 1
            pos_sum += len(open_pos)
    return curve, days_inv / len(calendar), pos_sum / max(days_inv, 1)


def metrics(curve):
    years = (calendar[-1] - calendar[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / years) - 1
    peak = curve[0]; mdd = 0.0
    for v in curve:
        peak = max(peak, v); mdd = max(mdd, (peak - v) / peak)
    rets = [curve[i] / curve[i-1] - 1 for i in range(1, len(curve))]
    m = sum(rets) / len(rets); var = sum((r-m)**2 for r in rets) / len(rets)
    sharpe = m / sqrt(var) * sqrt(252) if var > 0 else 0
    return cagr, mdd, (cagr / mdd if mdd else 0), sharpe


configs = [
    ("target2.5  index-gate ON",  "target_close", 2.5, True,  8),
    ("target2.5  index-gate OFF", "target_close", 2.5, False, 8),
    ("target2.5  OFF, max15pos",  "target_close", 2.5, False, 15),
    ("ladder     OFF, max15pos",  "ladder",       2.0, False, 15),
    ("chandelier OFF, max15pos",  "chandelier",   2.0, False, 15),
]

print(f"\n{'config':28}{'#tr':>5}{'deploy%':>8}{'avgPos':>7}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}{'finalEq':>11}")
print("-" * 90)
for label, mode, tr, reg, mp in configs:
    t0 = time.time()
    trades = gen_trades(mode, tr, reg)
    curve, dep, avgpos = run_portfolio(trades, max_pos=mp)
    c = metrics(curve)
    print(f"{label:28}{len(trades):>5}{dep:>8.0%}{avgpos:>7.1f}{c[0]:>8.1%}{c[1]:>8.1%}"
          f"{c[2]:>8.2f}{c[3]:>8.2f}{curve[-1]:>11,.0f}")

bench = [idx_close[d] for d in calendar]
bc = metrics(bench)
print("-" * 90)
print(f"{'NIFTY 500 buy&hold':28}{'—':>5}{'100%':>8}{'—':>7}{bc[0]:>8.1%}{bc[1]:>8.1%}{bc[2]:>8.2f}{bc[3]:>8.2f}"
      f"{START_CAP*Decimal(bench[-1]/bench[0]):>11,.0f}")
print("\nIf index-gate OFF lifts deploy% and CAGR without wrecking maxDD -> the per-stock")
print("stop IS sufficient downside protection, and the index gate was throttling us.")
