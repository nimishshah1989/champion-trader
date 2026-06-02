"""Final confirmation of the locked strategy + numbers for the Strategy Card.

Locked: chand5x (5x ATR trailing close-based stop), NO index gate, per-stock
Stage-2 strength + close-based stop as protection, RPT 0.25%, bear-scaled sizing
0.25x when index < rising 50DMA, max 15 concurrent, idle cash @ 6.5%.

Reports: DD-circuit-breaker comparison, train/test/full, per-year, monthly cash
drag, and writes the equity curve to a CSV.
"""
import csv
import sqlite3
import sys
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
DAILY_YIELD = (1 + 0.065) ** (1 / 252) - 1
cm = CostModel()

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
FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}
TRAIN = [d for d in FULL if d.year < 2021]
TEST = [d for d in FULL if d.year >= 2021]

trades = []
for s, (bs, df) in all_bars.items():
    trades += _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                             slippage=DEFAULT_SLIPPAGE, min_trp=2.0, start_date=START,
                             use_regime=False, regime_map=regime_map)


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(cal, *, rpt_pct=0.25, bear_frac=0.25, dd_halt=0.15, max_pos=15):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    rpt = Decimal(str(rpt_pct)); resume = dd_halt * 0.5 if dd_halt < 1 else 1.0
    cash = START_CAP; op = []; curve = []; peak = float(START_CAP); halted = False
    inv = pos = 0
    for d in cal:
        cash *= Decimal(1 + DAILY_YIELD)
        still = []
        for p in op:
            if p["xd"] == d:
                pr = Decimal(p["sh"]) * p["xp"]; cash += pr - cm.sell_costs(pr)
            else:
                still.append(p)
        op = still
        for p in op:
            p["px"] = lc(p["s"], d, p["px"])
        eq = cash + sum(Decimal(p["sh"]) * p["px"] for p in op)
        peak = max(peak, float(eq))
        if float(eq) < peak * (1 - dd_halt):
            halted = True
        elif float(eq) > peak * (1 - resume):
            halted = False
        if not halted:
            mult = Decimal("1.0") if regime_map.get(d, False) else Decimal(str(bear_frac))
            for t in eo.get(d, []):
                if len(op) >= max_pos:
                    continue
                sh = int((eq * rpt * mult / Decimal(100)) / t.stopdist)
                if sh <= 0:
                    continue
                cost = Decimal(sh) * t.entry; tot = cost + cm.buy_costs(cost)
                if tot > cash:
                    continue
                cash -= tot
                op.append({"s": t.symbol, "sh": sh, "xd": t.exit_date, "xp": t.exit, "px": t.entry})
        eq = cash + sum(Decimal(p["sh"]) * p["px"] for p in op)
        curve.append(float(eq))
        if op:
            inv += 1; pos += len(op)
    return curve, inv / len(cal), pos / max(inv, 1)


def met(curve, cal):
    yrs = (cal[-1] - cal[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / yrs) - 1
    pk = curve[0]; mdd = 0
    for v in curve:
        pk = max(pk, v); mdd = max(mdd, (pk - v) / pk)
    rets = [curve[i] / curve[i-1] - 1 for i in range(1, len(curve))]
    m = sum(rets) / len(rets); var = sum((r-m)**2 for r in rets) / len(rets)
    return cagr, mdd, (cagr / mdd if mdd else 0), (m / sqrt(var) * sqrt(252) if var > 0 else 0)


print("DD circuit-breaker comparison (chand5x, RPT0.25, bearF0.25, max15):\n")
print(f"{'ddHalt':>8}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}")
for halt in [1.0, 0.20, 0.15]:
    c, _, _ = portfolio(FULL, dd_halt=halt)
    m = met(c, FULL)
    print(f"{('none' if halt==1 else f'{halt:.0%}'):>8}{m[0]:>8.1%}{m[1]:>8.1%}{m[2]:>8.2f}{m[3]:>8.2f}")

print("\nLOCKED config: chand5x, RPT0.25, bearF0.25, ddHalt15%, max15, idle cash 6.5%\n")
for name, cal in [("TRAIN 2016-20", TRAIN), ("TEST 2021-26", TEST), ("FULL 2016-26", FULL)]:
    c, dep, ap = portfolio(cal, dd_halt=0.15)
    m = met(c, cal)
    b = met([idx_close[d] for d in cal], cal)
    print(f"{name:14} system: CAGR {m[0]:>6.1%}  maxDD {m[1]:>5.1%}  Calmar {m[2]:.2f}  Sharpe {m[3]:.2f}  "
          f"deploy {dep:.0%} avgPos {ap:.1f}   |  B&H {b[0]:.1%}/{b[1]:.0%}DD/{b[2]:.2f}")

# per-year + equity curve
curve, _, _ = portfolio(FULL, dd_halt=0.15)
yr = defaultdict(list)
for i, d in enumerate(FULL):
    yr[d.year].append(curve[i])
print("\nPer-year (system vs NIFTY500):")
print(f"{'year':6}{'sys ret':>9}{'sys DD':>8}{'idx ret':>9}")
idx_yr = defaultdict(list)
for d in FULL:
    idx_yr[d.year].append(idx_close[d])
for y in sorted(yr):
    seg = yr[y]; ret = seg[-1]/seg[0]-1
    pk = seg[0]; dd = 0
    for v in seg:
        pk = max(pk, v); dd = max(dd, (pk-v)/pk)
    iseg = idx_yr[y]; iret = iseg[-1]/iseg[0]-1
    print(f"{y:6}{ret:>9.1%}{dd:>8.1%}{iret:>9.1%}")

print(f"\nFinal: ₹1,00,000 -> ₹{curve[-1]:,.0f}  (buy&hold -> ₹{START_CAP*Decimal(idx_close[FULL[-1]]/idx_close[FULL[0]]):,.0f})")

with open("/home/user/champion-trader/equity_curve.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "system_equity", "nifty500_norm"])
    base = idx_close[FULL[0]]
    for i, d in enumerate(FULL):
        w.writerow([d.isoformat(), round(curve[i], 2), round(float(START_CAP) * idx_close[d] / base, 2)])
print("equity_curve.csv written")
