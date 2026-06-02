"""Robustness: does the edge survive in LIQUID names, or is it a small-cap artifact?

The headline result trades the full ~1270-name universe incl. illiquid small-caps.
The honest capacity question: if we restrict to the most-liquid names (tradeable
at real size with low slippage), does the strategy still work? If the edge holds
in the top-250/500 by turnover, it's a real, scalable edge. If it only works in
the illiquid tail, that's a capacity red flag.

Tier by median daily turnover (close*volume). Run the LOCKED config on each tier.
"""
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from math import sqrt
from statistics import median

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
all_bars, close_lookup, adt = {}, {}, {}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    all_bars[s] = (bs, precompute_features(bs))
    close_lookup[s] = {b.date: b.close for b in bs}
    # median daily turnover in ₹ crore (robust to spikes)
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    adt[s] = median(tnv) / 1e7 if tnv else 0
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}

# all trades once, then filter by tier
trades = []
for s, (bs, df) in all_bars.items():
    for t in _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                            slippage=DEFAULT_SLIPPAGE, min_trp=2.0, start_date=START,
                            use_regime=False, regime_map=regime_map):
        trades.append(t)

ranked = sorted(adt, key=lambda s: -adt[s])


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(allowed, *, rpt_pct=0.25, bear_frac=0.25, dd_halt=0.15, max_pos=15):
    eo = defaultdict(list)
    for t in trades:
        if t.symbol in allowed:
            eo[t.entry_date].append(t)
    rpt = Decimal(str(rpt_pct)); resume = dd_halt * 0.5
    cash = START_CAP; op = []; curve = []; peak = float(START_CAP); halted = False
    inv = pos = ntr = 0
    for d in FULL:
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
                cash -= tot; ntr += 1
                op.append({"s": t.symbol, "sh": sh, "xd": t.exit_date, "xp": t.exit, "px": t.entry})
        eq = cash + sum(Decimal(p["sh"]) * p["px"] for p in op)
        curve.append(float(eq))
        if op:
            inv += 1; pos += len(op)
    return curve, ntr, inv / len(FULL), pos / max(inv, 1)


def met(curve):
    yrs = (FULL[-1] - FULL[0]).days / 365.25
    cagr = (curve[-1] / curve[0]) ** (1 / yrs) - 1
    pk = curve[0]; mdd = 0
    for v in curve:
        pk = max(pk, v); mdd = max(mdd, (pk - v) / pk)
    rets = [curve[i] / curve[i-1] - 1 for i in range(1, len(curve))]
    m = sum(rets) / len(rets); var = sum((r-m)**2 for r in rets) / len(rets)
    return cagr, mdd, (cagr / mdd if mdd else 0), (m / sqrt(var) * sqrt(252) if var > 0 else 0)


print("Liquidity-tier robustness (locked config, full period). ADT = median daily turnover.\n")
print(f"{'universe':22}{'min ADT':>9}{'#trades':>8}{'avgPos':>7}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}")
print("-" * 80)
for label, n in [("top 100 (most liquid)", 100), ("top 250", 250), ("top 500", 500),
                 ("top 800", 800), ("full ~1270", len(ranked))]:
    tier = set(ranked[:n])
    min_adt = adt[ranked[min(n, len(ranked)) - 1]]
    curve, ntr, dep, ap = portfolio(tier)
    m = met(curve)
    print(f"{label:22}{min_adt:>8.1f}cr{ntr:>8}{ap:>7.1f}{m[0]:>8.1%}{m[1]:>8.1%}{m[2]:>8.2f}{m[3]:>8.2f}")

b = met([idx_close[d] for d in FULL])
print("-" * 80)
print(f"{'NIFTY500 buy&hold':22}{'':>9}{'':>8}{'':>7}{b[0]:>8.1%}{b[1]:>8.1%}{b[2]:>8.2f}{b[3]:>8.2f}")
print("\nIf top-250/500 still beats buy&hold -> edge is real & tradeable at size (not")
print("a micro-cap slippage artifact). Degradation toward the liquid top is expected.")
