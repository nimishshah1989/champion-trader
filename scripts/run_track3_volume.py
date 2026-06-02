"""TRACK 3: do the evidence-backed VOLUME filters add edge?

Tested on the honest baseline (tiered slippage + circuit-skip) with deterministic
momentum-rank selection (so differences are purely the volume filter, not noise):
  BASELINE         no volume gate
  DRY-UP           base volume contracts: mean(vol,10) < 0.8*mean(vol,50)  [Minervini/Wyckoff]
  BREAKOUT vol Kx  breakout-bar volume >= K * 50d avg, K in {1.5,2.0,2.5}   [O'Neil/Weinstein]
  DRY-UP + 2.0x    both

Report CAGR/DD/Calmar/Sharpe on TRAIN/TEST/FULL, plus #trades and win% (filters
shrink the sample -> wider error bars). Per the research, expect a MODEST effect;
the lift must clearly beat baseline on TEST to be worth the lost trades.
"""
import sqlite3
import sys
import warnings
from collections import defaultdict
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
cm = CostModel()


def slip_for_adt(a):
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
TRAIN = [d for d in FULL if d.year < 2021]
TEST = [d for d in FULL if d.year >= 2021]


def gen(**kw):
    raw = []
    for s, (bs, df) in all_bars.items():
        raw += _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                              slippage=slip_for_adt(adt[s]), min_trp=2.0, start_date=START,
                              use_regime=False, regime_map=regime_map, skip_circuit_locked=True, **kw)
    return raw


def lc(sym, d, fb):
    return close_lookup.get(sym, {}).get(d, fb)


def portfolio(trades, cal, *, rpt_pct=0.25, bear_frac=0.25, dd_halt=0.15, max_pos=15):
    eo = defaultdict(list)
    for t in trades:
        eo[t.entry_date].append(t)
    for d in eo:
        eo[d].sort(key=lambda t: score_lookup.get((t.symbol, t.entry_date), -1e9), reverse=True)
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


def winrate(trades):
    rs = [float((t.exit - t.entry) / t.stopdist) for t in trades]
    return (sum(1 for r in rs if r > 0) / len(rs), float(np.mean(rs))) if rs else (0, 0)


CONFIGS = [
    ("BASELINE", {}),
    ("DRY-UP 0.8", dict(vol_dryup=True, vol_dryup_ratio=0.8)),
    ("BREAKOUT 1.5x", dict(vol_breakout_k=1.5)),
    ("BREAKOUT 2.0x", dict(vol_breakout_k=2.0)),
    ("BREAKOUT 2.5x", dict(vol_breakout_k=2.5)),
    ("DRYUP + 2.0x", dict(vol_dryup=True, vol_breakout_k=2.0)),
]

print(f"{'config':14}{'#tr':>5}{'win%':>6}{'meanR':>7}  "
      f"{'TRAIN cal':>10}{'TEST cal':>10}{'FULL cal':>10}{'FULL cagr':>11}{'FULL dd':>9}")
print("-" * 92)
for label, kw in CONFIGS:
    tr = gen(**kw)
    w, mr = winrate(tr)
    ctr, cte, cfu = met(portfolio(tr, TRAIN), TRAIN), met(portfolio(tr, TEST), TEST), met(portfolio(tr, FULL), FULL)
    print(f"{label:14}{len(tr):>5}{w:>6.0%}{mr:>+7.2f}  "
          f"{ctr[2]:>10.2f}{cte[2]:>10.2f}{cfu[2]:>10.2f}{cfu[0]:>11.1%}{cfu[1]:>9.1%}")
print("-" * 92)
print("Filters must beat BASELINE on TEST Calmar AND keep enough trades. Per the research,")
print("expect modest; a big drop in #trades with no Calmar gain = the filter is just noise.")

# REDEPLOY: breakout >=2x raises trade QUALITY (35% win, +2.23R) but cuts trade count,
# leaving idle capital. Higher per-trade confidence => can we size up to recover CAGR
# while keeping the higher win rate + lower DD?
print("\nRedeploy test: breakout>=2.0x quality filter at higher RPT (vs baseline RPT0.25):")
print(f"{'config':22}{'RPT':>5}{'TRAIN cal':>10}{'TEST cal':>10}{'FULL cal':>10}{'FULL cagr':>11}{'FULL dd':>9}")
base_tr = gen()
m = met(portfolio(base_tr, FULL), FULL)
mt = met(portfolio(base_tr, TEST), TEST); mtr = met(portfolio(base_tr, TRAIN), TRAIN)
print(f"{'baseline (no filter)':22}{0.25:>5}{mtr[2]:>10.2f}{mt[2]:>10.2f}{m[2]:>10.2f}{m[0]:>11.1%}{m[1]:>9.1%}")
bk = gen(vol_breakout_k=2.0)
for rpt in [0.25, 0.35, 0.50]:
    cfu = met(portfolio(bk, FULL, rpt_pct=rpt), FULL)
    cte = met(portfolio(bk, TEST, rpt_pct=rpt), TEST)
    ctr = met(portfolio(bk, TRAIN, rpt_pct=rpt), TRAIN)
    print(f"{'breakout>=2.0x':22}{rpt:>5}{ctr[2]:>10.2f}{cte[2]:>10.2f}{cfu[2]:>10.2f}{cfu[0]:>11.1%}{cfu[1]:>9.1%}")
print("If breakout>=2.0x at higher RPT matches baseline CAGR with higher win% + lower/equal")
print("DD + better TEST Calmar -> the quality filter + sizing IS the win-rate-and-return synthesis.")
