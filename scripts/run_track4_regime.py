"""TRACK 4: regime-CONDITIONAL volume filter (no new fitted parameters).

Reuse the existing regime signal (NIFTY 500 above rising 50-DMA = the bear-sizing
signal). Generate the full breakout universe once, tag each trade with its
breakout-day volume ratio and the regime at entry, then gate at the portfolio layer:

  v1   : take all breakouts                                  (no filter)
  v2   : take only vol>=2x                                   (always filter)
  RC   : bull regime -> take all; weak regime -> need vol>=2x (filter when it's hard)
  RC-inv (sanity): weak -> take all; bull -> need vol>=2x     (should be WORSE if RC is real)

All run at the same RPT so the ONLY variable is the filter logic. Walk-forward
(TRAIN 16-20 / TEST 21-26) + per-year. Honest baseline (tiered slippage +
circuit-skip) and deterministic momentum-rank throughout.
"""
import sqlite3
import sys
import warnings
from collections import defaultdict, OrderedDict
from datetime import date
from decimal import Decimal
from math import sqrt
from statistics import median

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars  # noqa: E402
from backend.engine.costs import CostModel                          # noqa: E402
from backend.engine.precompute import precompute_features           # noqa: E402
from backend.engine.regime import load_regime                       # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
START_CAP = Decimal("100000")
DAILY_YIELD = (1 + 0.065) ** (1 / 252) - 1
RPT = 0.35
cm = CostModel()


def slip(a):
    return Decimal("0.0010") if a >= 15 else Decimal("0.0025") if a >= 5 else Decimal("0.0050") if a >= 1 else Decimal("0.0100")


regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
WEAK = frozenset(d for d, v in regime_map.items() if not v)    # filter here for RC
BULL = frozenset(d for d, v in regime_map.items() if v)        # filter here for RC-inv

# (vol_breakout_k, vol_filter_dates): entries re-derived inside the engine per config.
CONFIGS = {
    "v1 (no filter)":    (0.0, None),
    "v2 (always 2x)":    (2.0, None),
    "RC (2x when weak)": (2.0, WEAK),
    "RC-inv (sanity)":   (2.0, BULL),
}

con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
close_lookup, score_lookup = {}, {}
sets = {name: [] for name in CONFIGS}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    close_lookup[s] = {b.date: b.close for b in bs}
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    sl = slip(median(tnv) / 1e7 if tnv else 0)
    c = df["close"].astype(float).to_numpy()
    r126 = np.full(len(c), np.nan); r252 = np.full(len(c), np.nan)
    r126[126:] = c[126:] / c[:-126] - 1
    r252[252:] = c[252:] / c[:-252] - 1
    dret = np.diff(c) / c[:-1]
    vol = np.full(len(c), np.nan)
    for k in range(252, len(c)):
        sd = dret[k-252:k].std(); vol[k] = sd if sd > 0 else np.nan
    sc = 0.5 * (r126 / vol) + 0.5 * (r252 / vol)
    for k in range(len(bs) - 1):
        if sc[k] == sc[k]:
            score_lookup[(s, bs[k + 1].date)] = float(sc[k])
    for name, (k, fdates) in CONFIGS.items():
        sets[name] += _fast_simulate(
            s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0, slippage=sl,
            min_trp=2.0, start_date=START, use_regime=False, regime_map=regime_map,
            skip_circuit_locked=True, vol_breakout_k=k, vol_filter_dates=fdates)
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}
TRAIN = [d for d in FULL if d.year < 2021]
TEST = [d for d in FULL if d.year >= 2021]


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(trades, cal, *, dd_halt=0.15, bear_frac=0.25, max_pos=15):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    for d in eo:
        eo[d].sort(key=lambda t: score_lookup.get((t.symbol, t.entry_date), -1e9), reverse=True)
    rpt = Decimal(str(RPT)); resume = dd_halt * 0.5
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
                op.append({"s": t.symbol, "sh": sh, "xd": t.exit_date, "xp": t.exit, "px": t.entry})
        eq = cash + sum(Decimal(p["sh"]) * p["px"] for p in op)
        curve.append((d, float(eq)))
    return curve


def met(curve, cal):
    vals = [v for _, v in curve]
    yrs = (cal[-1] - cal[0]).days / 365.25
    cagr = (vals[-1] / vals[0]) ** (1 / yrs) - 1
    pk = vals[0]; mdd = 0
    for v in vals:
        pk = max(pk, v); mdd = max(mdd, (pk - v) / pk)
    rets = [vals[i] / vals[i-1] - 1 for i in range(1, len(vals))]
    m = sum(rets) / len(rets); var = sum((x-m)**2 for x in rets) / len(rets)
    return cagr, mdd, (cagr / mdd if mdd else 0), (m / sqrt(var) * sqrt(252) if var > 0 else 0)


def yearly(curve):
    end = OrderedDict()
    for d, v in curve:
        end[d.year] = v
    res = OrderedDict(); prev = float(START_CAP)
    for y, v in end.items():
        res[y] = v / prev - 1; prev = v
    return res


print(f"all at RPT {RPT}%   (v1 universe = {len(sets['v1 (no filter)'])} breakouts)\n")
print(f"{'config':20}{'#tr':>5}{'TRAIN cal':>11}{'TEST cal':>10}{'FULL cal':>10}{'FULL cagr':>11}{'FULL dd':>9}")
print("-" * 76)
curves_full = {}
for name in CONFIGS:
    tr = sets[name]
    ctr, cte = met(portfolio(tr, TRAIN), TRAIN), met(portfolio(tr, TEST), TEST)
    cf = portfolio(tr, FULL); cfu = met(cf, FULL); curves_full[name] = cf
    print(f"{name:20}{len(tr):>5}{ctr[2]:>11.2f}{cte[2]:>10.2f}{cfu[2]:>10.2f}{cfu[0]:>11.1%}{cfu[1]:>9.1%}")
print("-" * 76)
print("sanity: v1=all trades, v2=only >=2x (should match engine's 805 / 293).\n")

ys = {name: yearly(curves_full[name]) for name in ["v1 (no filter)", "v2 (always 2x)", "RC (2x when weak)"]}
yi = yearly([(d, idx_close[d] * float(START_CAP) / idx_close[FULL[0]]) for d in FULL])
print("Per-year returns (did RC capture v1's bull-year upside AND v2's selective-market edge?)")
print(f"{'year':>6}{'v1':>9}{'v2':>9}{'RC':>9}{'NIFTY500':>10}   bull days")
bull = defaultdict(lambda: [0, 0])
for d in FULL:
    bull[d.year][0 if regime_map.get(d, False) else 1] += 1
for y in ys["v1 (no filter)"]:
    bd = bull[y]; pct = bd[0] / (bd[0] + bd[1])
    print(f"{y:>6}{ys['v1 (no filter)'][y]:>9.1%}{ys['v2 (always 2x)'][y]:>9.1%}"
          f"{ys['RC (2x when weak)'][y]:>9.1%}{yi[y]:>10.1%}   {pct:>4.0%} bull")

# our honest yardstick: strip the 2021 melt-up
span = (FULL[-1] - FULL[0]).days / 365.25 - 1.0
print(f"\nEx-2021 CAGR (compound all years except 2021, ~{span:.1f}y):")
for name in ["v1 (no filter)", "v2 (always 2x)", "RC (2x when weak)"]:
    fac = 1.0
    for y, r in ys[name].items():
        if y != 2021:
            fac *= (1 + r)
    print(f"  {name:20}{fac ** (1/span) - 1:>7.1%}")
print("\nWALK-FORWARD READ (trust TEST 21-26, not FULL): v2 TEST Calmar 2.34 vs RC 0.46.")
print("RC rides 2021 like v1 (inflates FULL CAGR) but gives up v2's 2023-25 selective edge")
print("-> the 50-DMA 'is market up?' signal can't tell easy-bull (2017/20) from selective-")
print("bull (23/24); both read 'bull', so RC drops the filter exactly when 23/24 needed it.")
