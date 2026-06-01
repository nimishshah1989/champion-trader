"""Autonomous strategy search — tame the upside engine's drawdown.

The ladder (let winners run, no index gate) earns 30.8% CAGR but 52.6% maxDD.
Goal: DOMINATE buy&hold (13.4% / 44.8% DD) on BOTH axes via risk overlays that
manage risk WITHOUT over-protecting (we still trade bears, just smarter):

  1. RPT scaling           - smaller bets => lower DD, proportionally lower CAGR
  2. regime-scaled sizing  - full size when index>rising-50DMA, BEAR_FRAC when not
                             (trade the bear-market trends, at reduced size)
  3. DD circuit-breaker    - halt NEW entries when portfolio DD>halt%, resume<resume%
                             (caps the crash tail; open winners keep running)

Trades depend only on the exit, so we generate them ONCE per exit mode and sweep
the (cheap) portfolio overlays. Leaderboard sorted by Calmar; we want high CAGR
with maxDD <~30%.
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

print("Preloading bars + features + trades...", flush=True)
t0 = time.time()
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


def gen_trades(exit_mode, target_r=2.0, chandelier_mult=3.0, use_regime=False):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode=exit_mode, target_r=target_r,
                              chandelier_mult=chandelier_mult, slippage=DEFAULT_SLIPPAGE,
                              min_trp=2.0, start_date=START, use_regime=use_regime,
                              regime_map=regime_map)
    return raw


def last_close(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(trades, *, rpt_pct=0.5, max_pos=15, bear_frac=1.0,
              dd_halt=1.0, dd_resume=1.0, cal=None):
    """Daily portfolio walk with regime-scaled sizing + DD circuit-breaker."""
    cal = cal or calendar
    entries_on = defaultdict(list)
    for t in trades:
        entries_on[t.entry_date].append(t)
    rpt = Decimal(str(rpt_pct))
    cash = START_CAP
    open_pos = []
    curve = []
    peak = float(START_CAP)
    halted = False
    days_inv = pos_sum = 0
    for d in cal:
        cash *= Decimal(1 + DAILY_YIELD)
        # close exits
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

        # circuit breaker state
        peak = max(peak, float(equity))
        if float(equity) < peak * (1 - dd_halt):
            halted = True
        elif float(equity) > peak * (1 - dd_resume):
            halted = False

        if not halted:
            size_mult = Decimal("1.0") if regime_map.get(d, False) else Decimal(str(bear_frac))
            for t in entries_on.get(d, []):
                if len(open_pos) >= max_pos:
                    continue
                shares = int((equity * rpt * size_mult / Decimal(100)) / t.stopdist)
                if shares <= 0:
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
    return curve, days_inv / len(cal), pos_sum / max(days_inv, 1)


def metrics(curve, cal=None):
    cal = cal or calendar
    years = (cal[-1] - cal[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / years) - 1
    peak = curve[0]; mdd = 0.0
    for v in curve:
        peak = max(peak, v); mdd = max(mdd, (peak - v) / peak)
    rets = [curve[i] / curve[i-1] - 1 for i in range(1, len(curve))]
    m = sum(rets) / len(rets); var = sum((r-m)**2 for r in rets) / len(rets)
    sharpe = m / sqrt(var) * sqrt(252) if var > 0 else 0
    return cagr, mdd, (cagr / mdd if mdd else 0), sharpe


print(f"  ready in {time.time()-t0:.0f}s. Generating trade sets...", flush=True)
TRADES = {
    "ladder":     gen_trades("ladder"),
    "chand3x":    gen_trades("chandelier", chandelier_mult=3.0),
    "chand5x":    gen_trades("chandelier", chandelier_mult=5.0),
}
for k, v in TRADES.items():
    print(f"    {k}: {len(v)} trades")

bench = [idx_close[d] for d in calendar]
bc = metrics(bench)

print(f"\n{'exit':9}{'rpt':>5}{'bearF':>6}{'ddHalt':>7}{'deploy%':>8}{'avgPos':>7}"
      f"{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}")
print("-" * 82)

results = []
grid = []
for exit_mode in ["ladder", "chand3x", "chand5x"]:
    for rpt in [0.5, 0.35, 0.25]:
        for bear in [1.0, 0.5, 0.25]:
            for halt in [1.0, 0.20, 0.15]:
                grid.append((exit_mode, rpt, bear, halt))

for exit_mode, rpt, bear, halt in grid:
    resume = halt * 0.5 if halt < 1.0 else 1.0
    curve, dep, avgpos = portfolio(TRADES[exit_mode], rpt_pct=rpt, bear_frac=bear,
                                   dd_halt=halt, dd_resume=resume)
    c = metrics(curve)
    results.append((exit_mode, rpt, bear, halt, dep, avgpos, c, curve[-1]))

# leaderboard: dominate buy&hold (CAGR>13.4 AND maxDD<44.8), sorted by Calmar
print("\n### TOP 15 BY CALMAR (maxDD < 35%) ###")
good = [r for r in results if r[6][1] < 0.35]
for r in sorted(good, key=lambda x: -x[6][2])[:15]:
    exit_mode, rpt, bear, halt, dep, avgpos, c, fin = r
    print(f"{exit_mode:9}{rpt:>5}{bear:>6}{halt:>7.2f}{dep:>8.0%}{avgpos:>7.1f}"
          f"{c[0]:>8.1%}{c[1]:>8.1%}{c[2]:>8.2f}{c[3]:>8.2f}")

print("\n### TOP 10 BY CAGR (maxDD < 30%) — 'optimize the top' ###")
topcagr = [r for r in results if r[6][1] < 0.30]
for r in sorted(topcagr, key=lambda x: -x[6][0])[:10]:
    exit_mode, rpt, bear, halt, dep, avgpos, c, fin = r
    print(f"{exit_mode:9}{rpt:>5}{bear:>6}{halt:>7.2f}{dep:>8.0%}{avgpos:>7.1f}"
          f"{c[0]:>8.1%}{c[1]:>8.1%}{c[2]:>8.2f}{c[3]:>8.2f}")

print("-" * 82)
print(f"{'NIFTY500 buy&hold':28}{'':>15}{bc[0]:>8.1%}{bc[1]:>8.1%}{bc[2]:>8.2f}{bc[3]:>8.2f}")
