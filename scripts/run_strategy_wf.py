"""Walk-forward the winning overlay config — is it real or overfit?

Rigorous protocol:
  1. Generate trades (chand 4x/5x/6x, no index gate) over the full period.
  2. SEARCH the overlay grid (rpt, bear_frac, dd_halt) on TRAIN ONLY (2016-2020),
     pick the best by Calmar with maxDD<30%.
  3. Apply that LOCKED config BLIND to TEST (2021-2026) and report.
  4. Per-year breakdown + tail-dependence check (top-trade P&L share).

If test-period Calmar stays well above buy&hold (0.30) and maxDD stays bounded,
the strategy generalises.
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


def gen_trades(exit_mode, chandelier_mult):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode=exit_mode, target_r=2.0,
                              chandelier_mult=chandelier_mult, slippage=DEFAULT_SLIPPAGE,
                              min_trp=2.0, start_date=START, use_regime=False, regime_map=regime_map)
    return raw


def last_close(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(trades, cal, *, rpt_pct, bear_frac, dd_halt, max_pos=15):
    entries_on = defaultdict(list)
    for t in trades:
        entries_on[t.entry_date].append(t)
    rpt = Decimal(str(rpt_pct)); dd_resume = dd_halt * 0.5 if dd_halt < 1 else 1.0
    cash = START_CAP; open_pos = []; curve = []; peak = float(START_CAP); halted = False
    for d in cal:
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
        peak = max(peak, float(equity))
        if float(equity) < peak * (1 - dd_halt):
            halted = True
        elif float(equity) > peak * (1 - dd_resume):
            halted = False
        if not halted:
            mult = Decimal("1.0") if regime_map.get(d, False) else Decimal(str(bear_frac))
            for t in entries_on.get(d, []):
                if len(open_pos) >= max_pos:
                    continue
                shares = int((equity * rpt * mult / Decimal(100)) / t.stopdist)
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
    return curve


def metrics(curve, cal):
    years = (cal[-1] - cal[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / years) - 1
    peak = curve[0]; mdd = 0.0
    for v in curve:
        peak = max(peak, v); mdd = max(mdd, (peak - v) / peak)
    rets = [curve[i] / curve[i-1] - 1 for i in range(1, len(curve))]
    m = sum(rets) / len(rets); var = sum((r-m)**2 for r in rets) / len(rets)
    sharpe = m / sqrt(var) * sqrt(252) if var > 0 else 0
    return cagr, mdd, (cagr / mdd if mdd else 0), sharpe


TR = {cm_: gen_trades("chandelier", cm_) for cm_ in [4.0, 5.0, 6.0]}

# 2. search overlays on TRAIN only
print("STEP 1: search overlays on TRAIN (2016-2020) only\n")
best = None
for cm_ in [4.0, 5.0, 6.0]:
    for rpt in [0.20, 0.25, 0.30]:
        for bear in [0.25, 0.5]:
            for halt in [0.15, 0.20]:
                cv = portfolio(TR[cm_], TRAIN, rpt_pct=rpt, bear_frac=bear, dd_halt=halt)
                c = metrics(cv, TRAIN)
                if c[1] < 0.30 and (best is None or c[2] > best[1][2]):
                    best = ((cm_, rpt, bear, halt), c)
(cm_b, rpt_b, bear_b, halt_b), ctr = best
print(f"  best TRAIN config: chand{cm_b}x  RPT{rpt_b}  bearF{bear_b}  ddHalt{halt_b}")
print(f"  TRAIN: CAGR {ctr[0]:.1%}  maxDD {ctr[1]:.1%}  Calmar {ctr[2]:.2f}  Sharpe {ctr[3]:.2f}\n")

# 3. apply BLIND to TEST
print("STEP 2: apply that LOCKED config BLIND to TEST (2021-2026)\n")
cv_test = portfolio(TR[cm_b], TEST, rpt_pct=rpt_b, bear_frac=bear_b, dd_halt=halt_b)
cte = metrics(cv_test, TEST)
cv_full = portfolio(TR[cm_b], FULL, rpt_pct=rpt_b, bear_frac=bear_b, dd_halt=halt_b)
cfu = metrics(cv_full, FULL)

def bench(cal):
    b = [idx_close[d] for d in cal]
    return metrics(b, cal)

print(f"{'window':16}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}   vs buy&hold")
for name, cal, c in [("TRAIN 16-20", TRAIN, ctr), ("TEST 21-26", TEST, cte), ("FULL 16-26", FULL, cfu)]:
    b = bench(cal)
    print(f"{name:16}{c[0]:>8.1%}{c[1]:>8.1%}{c[2]:>8.2f}{c[3]:>8.2f}   "
          f"B&H: {b[0]:.1%}/{b[1]:.0%}DD/Calmar {b[2]:.2f}")

# 4. per-year + tail check on full
print("\nSTEP 3: per-year (full-period run) + tail-dependence check")
import numpy as np
cv = cv_full
yr_idx = defaultdict(list)
for i, d in enumerate(FULL):
    yr_idx[d.year].append(cv[i])
print(f"\n{'year':6}{'ret%':>8}{'maxDD%':>8}")
for y in sorted(yr_idx):
    seg = yr_idx[y]
    ret = seg[-1] / seg[0] - 1
    pk = seg[0]; dd = 0
    for v in seg:
        pk = max(pk, v); dd = max(dd, (pk - v) / pk)
    print(f"{y:6}{ret:>8.1%}{dd:>8.1%}")

# tail dependence: per-trade R distribution on the chosen exit
rs = []
for t in TR[cm_b]:
    rs.append(float((t.exit - t.entry) / t.stopdist))
wins = sorted([r for r in rs if r > 0], reverse=True)
top5_share = sum(wins[:5]) / sum(wins) if wins else 0
print(f"\nPer-trade edge (chand{cm_b}x): {len(rs)} trades, win {sum(1 for r in rs if r>0)/len(rs):.0%}, "
      f"mean {np.mean(rs):+.2f}R, top-5 winners = {top5_share:.0%} of gross profit")
print("(top-5 share <10% on ~800 trades = distributed, not a lottery)")
