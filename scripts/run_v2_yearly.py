"""Per-year returns of v1 vs v2, walking ONE continuous equity curve each.

v1 = honest baseline (tiered slippage + circuit-skip), momentum-rank, RPT 0.25, no vol filter
v2 = same + breakout-volume >= 2x 50d avg, RPT 0.35
Yearly return[Y] = equity(end of Y) / equity(end of Y-1) - 1 (first year from START_CAP).
"""
import sqlite3
import sys
import warnings
from collections import defaultdict, OrderedDict
from datetime import date
from decimal import Decimal
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
cm = CostModel()


def slip(a):
    return Decimal("0.0010") if a >= 15 else Decimal("0.0025") if a >= 5 else Decimal("0.0050") if a >= 1 else Decimal("0.0100")


regime_map, _ = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
all_bars, close_lookup, adt, score_lookup = {}, {}, {}, {}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    all_bars[s] = (bs, df)
    close_lookup[s] = {b.date: b.close for b in bs}
    tnv = sorted(float(b.close) * b.volume for b in bs[-1000:])
    adt[s] = median(tnv) / 1e7 if tnv else 0
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
idx = con.execute("select date, close from index_bars where index_code='NIFTY 500' order by date").fetchall()
con.close()
FULL = [date.fromisoformat(d) for d, _ in idx if date.fromisoformat(d) >= START]
idx_close = {date.fromisoformat(d): float(c) for d, c in idx}


def gen(**kw):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                              slippage=slip(adt[s]), min_trp=2.0, start_date=START, use_regime=False,
                              regime_map=regime_map, skip_circuit_locked=True, **kw)
    return raw


def curve_with_dates(trades, *, rpt_pct, dd_halt=0.15, bear_frac=0.25, max_pos=15):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    for d in eo:
        eo[d].sort(key=lambda t: score_lookup.get((t.symbol, t.entry_date), -1e9), reverse=True)
    rpt = Decimal(str(rpt_pct)); resume = dd_halt * 0.5
    cash = START_CAP; op = []; peak = float(START_CAP); halted = False
    out = []
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
            p["px"] = close_lookup.get(p["s"], {}).get(d, p["px"])
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
        out.append((d, float(eq)))
    return out


def yearly(curve):
    """year -> (return, n_trading_days). Return measured end-of-year vs prior end-of-year."""
    end = OrderedDict()
    for d, v in curve:
        end[d.year] = v
    days = defaultdict(int)
    for d, _ in curve:
        days[d.year] += 1
    res = OrderedDict()
    prev = float(START_CAP)
    for y, v in end.items():
        res[y] = (v / prev - 1, days[y])
        prev = v
    return res


v1 = curve_with_dates(gen(), rpt_pct=0.25)
v2 = curve_with_dates(gen(vol_breakout_k=2.0), rpt_pct=0.35)
y1, y2 = yearly(v1), yearly(v2)

# index (buy & hold) yearly for context -- rebased so it starts at START_CAP
_f = float(START_CAP) / idx_close[FULL[0]]
idx_curve = [(d, idx_close[d] * _f) for d in FULL]
yi = yearly(idx_curve)

print(f"data: {FULL[0]} -> {FULL[-1]}\n")
print(f"{'year':>6}{'days':>6}{'v1 ret':>10}{'v2 ret':>10}{'NIFTY500':>11}   note")
print("-" * 62)
for y in y1:
    note = ""
    if y == FULL[0].year:
        note = f"partial (from {FULL[0].strftime('%b %d')})"
    elif y == FULL[-1].year:
        note = f"partial (to {FULL[-1].strftime('%b %d')})"
    print(f"{y:>6}{y1[y][1]:>6}{y1[y][0]:>10.1%}{y2[y][0]:>10.1%}{yi[y][0]:>11.1%}   {note}")
print("-" * 62)


def cagr(curve):
    yrs = (curve[-1][0] - curve[0][0]).days / 365.25
    return (curve[-1][1] / float(START_CAP)) ** (1 / yrs) - 1


print(f"{'CAGR':>6}{'':>6}{cagr(v1):>10.1%}{cagr(v2):>10.1%}{cagr(idx_curve):>11.1%}   (full-period compound)")
# v2 ex-best-year sanity
rs = [v for v, _ in y2.values()]
best = max(range(len(rs)), key=lambda i: rs[i])
yrs_list = list(y2.keys())
print(f"\nv2 best year: {yrs_list[best]} ({rs[best]:+.1%}). "
      f"v2 worst year: {yrs_list[min(range(len(rs)), key=lambda i: rs[i])]} "
      f"({min(rs):+.1%}).")
print(f"v2 positive years: {sum(1 for r in rs if r > 0)}/{len(rs)}")


def cagr_excl(yres, drop_year):
    fac = 1.0; days = 0
    for y, (r, dd) in yres.items():
        if y == drop_year:
            continue
        fac *= (1 + r); days += dd
    return fac ** (252 / days) - 1


print(f"\nExcluding the 2021 melt-up year:  v1 CAGR {cagr_excl(y1, 2021):.1%}   "
      f"v2 CAGR {cagr_excl(y2, 2021):.1%}   NIFTY500 {cagr_excl(yi, 2021):.1%}")
