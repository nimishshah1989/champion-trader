"""Exit shootout under the winning risk overlays: which exit is best AND consistent?

chand6x won on Calmar but is tail-dependent (26% win, top-5=20% of profit). Test
the hybrid (book half at target_r, trail the rest wide) against ladder & chandelier
under the same overlays (RPT 0.25-0.3, bearF 0.25, ddHalt 0.15, max15, no gate),
with a TRAIN/TEST split. Report CAGR/DD/Calmar/Sharpe + per-trade win% and top-5
concentration so we can pick high return WITH consistency (the user's profile).
"""
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from math import sqrt

import numpy as np

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


def gen(exit_mode, target_r=2.5, cmult=5.0):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode=exit_mode, target_r=target_r,
                              chandelier_mult=cmult, slippage=DEFAULT_SLIPPAGE, min_trp=2.0,
                              start_date=START, use_regime=False, regime_map=regime_map)
    return raw


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(trades, cal, *, rpt_pct=0.3, bear_frac=0.25, dd_halt=0.15, max_pos=15):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    rpt = Decimal(str(rpt_pct)); resume = dd_halt * 0.5
    cash = START_CAP; op = []; curve = []; peak = float(START_CAP); halted = False
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
                op.append({"s": t.symbol, "sh": sh, "stopdist": t.stopdist,
                           "xd": t.exit_date, "xp": t.exit, "px": t.entry})
        eq = cash + sum(Decimal(p["sh"]) * p["px"] for p in op)
        curve.append(float(eq))
    return curve


def met(curve, cal):
    yrs = (cal[-1] - cal[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / yrs) - 1
    pk = curve[0]; mdd = 0
    for v in curve:
        pk = max(pk, v); mdd = max(mdd, (pk - v) / pk)
    rets = [curve[i] / curve[i-1] - 1 for i in range(1, len(curve))]
    m = sum(rets) / len(rets); var = sum((r-m)**2 for r in rets) / len(rets)
    return cagr, mdd, (cagr / mdd if mdd else 0), (m / sqrt(var) * sqrt(252) if var > 0 else 0)


def tail(trades):
    rs = [float((t.exit - t.entry) / t.stopdist) for t in trades]
    w = sorted([r for r in rs if r > 0], reverse=True)
    return (sum(1 for r in rs if r > 0) / len(rs), float(np.mean(rs)),
            sum(w[:5]) / sum(w) if w else 0)


EXITS = {
    "ladder":      gen("ladder"),
    "hybrid 2.5R": gen("hybrid", target_r=2.5, cmult=5.0),
    "hybrid 3.0R": gen("hybrid", target_r=3.0, cmult=5.0),
    "chand5x":     gen("chandelier", cmult=5.0),
    "chand6x":     gen("chandelier", cmult=6.0),
}

print("Exit shootout  (RPT0.3 bearF0.25 ddHalt15% max15, no gate)\n")
print(f"{'exit':12}{'win%':>6}{'meanR':>7}{'top5%':>7}  |  "
      f"{'TRAIN cagr/dd/cal':>22}  {'TEST cagr/dd/cal':>22}  {'FULL cagr/dd/cal/shrp':>26}")
print("-" * 110)
for name, tr in EXITS.items():
    w, mr, t5 = tail(tr)
    ctr = met(portfolio(tr, TRAIN), TRAIN)
    cte = met(portfolio(tr, TEST), TEST)
    cfu = met(portfolio(tr, FULL), FULL)
    print(f"{name:12}{w:>6.0%}{mr:>+7.2f}{t5:>7.0%}  |  "
          f"{ctr[0]:>7.1%}/{ctr[1]:>4.0%}/{ctr[2]:>4.2f}      "
          f"{cte[0]:>7.1%}/{cte[1]:>4.0%}/{cte[2]:>4.2f}      "
          f"{cfu[0]:>7.1%}/{cfu[1]:>4.0%}/{cfu[2]:>4.2f}/{cfu[3]:>4.2f}")

b = [idx_close[d] for d in TEST]; bt = met(b, TEST)
bf = [idx_close[d] for d in FULL]; bff = met(bf, FULL)
print("-" * 110)
print(f"{'buy&hold':12}{'':19}  |  {'':24}{bt[0]:>7.1%}/{bt[1]:>4.0%}/{bt[2]:>4.2f}      "
      f"{bff[0]:>7.1%}/{bff[1]:>4.0%}/{bff[2]:>4.2f}/{bff[3]:>4.2f}")
print("\nWant: high CAGR, low DD, HIGH win%, LOW top5% (consistent, not a lottery), TEST holds.")
