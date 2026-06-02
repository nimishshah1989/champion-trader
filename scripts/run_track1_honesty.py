"""TRACK 1 (honesty): how much of the 24.5% survives realistic frictions?

The India research flagged two optimistic assumptions in our backtest:
  1. flat 10bps slippage  -> small/mid-caps have far wider spreads (NSE impact cost)
  2. breakouts always fill -> a breakout that locks at the upper circuit is unfillable

Re-run the LOCKED config (chand5x, RPT0.25, bearF0.25, ddHalt15%, max15) under:
  OPTIMISTIC: flat 10bps, fills assumed            (current headline)
  HONEST:     slippage tiered by liquidity (ADV) + skip circuit-locked breakouts
on TRAIN / TEST / FULL. If HONEST stays well above buy&hold, the edge is real.
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
from backend.engine.precompute import precompute_features           # noqa: E402
from backend.engine.regime import load_regime                       # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
START_CAP = Decimal("100000")
DAILY_YIELD = (1 + 0.065) ** (1 / 252) - 1
cm = CostModel()


def slip_for_adt(adt_cr):
    """Half-spread / impact proxy by median daily turnover (₹ crore), each side."""
    if adt_cr >= 15:
        return Decimal("0.0010")    # 10 bps  - liquid (top-500-ish)
    if adt_cr >= 5:
        return Decimal("0.0025")    # 25 bps
    if adt_cr >= 1:
        return Decimal("0.0050")    # 50 bps
    return Decimal("0.0100")        # 100 bps - microcap, wide spread


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
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    adt[s] = median(tnv) / 1e7 if tnv else 0
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}
TRAIN = [d for d in FULL if d.year < 2021]
TEST = [d for d in FULL if d.year >= 2021]


def gen_trades(*, tiered_slip, circuit_skip):
    raw = []
    for s, (bs, df) in all_bars.items():
        slip = slip_for_adt(adt[s]) if tiered_slip else Decimal("0.0010")
        raw += _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                              slippage=slip, min_trp=2.0, start_date=START, use_regime=False,
                              regime_map=regime_map, skip_circuit_locked=circuit_skip)
    return raw


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(trades, cal, *, rpt_pct=0.25, bear_frac=0.25, dd_halt=0.15, max_pos=15, shuffle_seed=None):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    if shuffle_seed is not None:
        import random
        rng = random.Random(shuffle_seed)
        for d in eo:
            rng.shuffle(eo[d])
    rpt = Decimal(str(rpt_pct)); resume = dd_halt * 0.5
    cash = START_CAP
    op = []
    curve = []
    peak = float(START_CAP)
    halted = False
    for d in cal:
        cash *= Decimal(1 + DAILY_YIELD)
        still = []
        for p in op:
            if p["xd"] == d:
                pr = Decimal(p["sh"]) * p["xp"]
                cash += pr - cm.sell_costs(pr)
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
                cost = Decimal(sh) * t.entry
                tot = cost + cm.buy_costs(cost)
                if tot > cash:
                    continue
                cash -= tot
                op.append({"s": t.symbol, "sh": sh, "xd": t.exit_date, "xp": t.exit, "px": t.entry})
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


opt = gen_trades(tiered_slip=False, circuit_skip=False)
hon = gen_trades(tiered_slip=True, circuit_skip=True)
print(f"trades: optimistic={len(opt)}  honest={len(hon)}  "
      f"(circuit-locked entries skipped: {len(opt) - len(hon)})\n")

print(f"{'model':12}{'window':14}{'CAGR':>8}{'maxDD':>8}{'Calmar':>8}{'Sharpe':>8}")
print("-" * 58)
for label, tr in [("OPTIMISTIC", opt), ("HONEST", hon)]:
    for name, cal in [("TRAIN 16-20", TRAIN), ("TEST 21-26", TEST), ("FULL 16-26", FULL)]:
        m = met(portfolio(tr, cal), cal)
        print(f"{label:12}{name:14}{m[0]:>8.1%}{m[1]:>8.1%}{m[2]:>8.2f}{m[3]:>8.2f}")
    print("-" * 58)
b = met([idx_close[d] for d in FULL], FULL)
print(f"{'buy&hold':12}{'FULL 16-26':14}{b[0]:>8.1%}{b[1]:>8.1%}{b[2]:>8.2f}{b[3]:>8.2f}")

# decompose the two effects on FULL (which one drives the change?)
slip_only = gen_trades(tiered_slip=True, circuit_skip=False)
circ_only = gen_trades(tiered_slip=False, circuit_skip=True)
print("\nDecomposition on FULL 16-26:")
for label, tr in [("slippage only", slip_only), ("circuit-skip only", circ_only)]:
    m = met(portfolio(tr, FULL), FULL)
    print(f"  {label:20}{m[0]:>8.1%} CAGR{m[1]:>8.1%} DD{m[2]:>8.2f} Calmar")
print("\n(slippage-only should be <=optimistic = real drag; circuit-skip-only isolates the")
print(" benefit of not chasing unfillable parabolic breakouts.)")

# SELECTION-ORDER NOISE: same trades, shuffle same-day order across seeds -> CAGR spread
print("\nSelection-order noise probe (HONEST trades, FULL, 12 random same-day orderings):")
cagrs, calmars = [], []
for seed in range(12):
    m = met(portfolio(hon, FULL, shuffle_seed=seed), FULL)
    cagrs.append(m[0]); calmars.append(m[2])
print(f"  CAGR : min {min(cagrs):.1%}  median {sorted(cagrs)[6]:.1%}  max {max(cagrs):.1%}  "
      f"(spread {max(cagrs)-min(cagrs):.1%})")
print(f"  Calmar: min {min(calmars):.2f}  median {sorted(calmars)[6]:.2f}  max {max(calmars):.2f}")
print("If the spread is several %, the single-number CAGR is selection-noise -> Track 2")
print("(principled momentum-rank selection) is needed for a stable, meaningful number.")
