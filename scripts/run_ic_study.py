"""Information Coefficient study — which features actually predict winners?

THE QUESTION: within our setup universe (stage S1B/S2 + contraction + valid base
+ trigger break), every signal currently gets taken equally. But do some setups
have higher forward returns than others? If a feature's rank correlates with the
forward outcome (high IC), we can SCORE setups and take only the best — turning a
35% win-rate filter into a selective, higher-win-rate strategy.

For every signal we record:
  - features at signal time (volatility, volume, trend, base quality, momentum, RS)
  - forward outcome labels:
      mfe_R_40    : max favourable excursion in R over next 40 bars (how big a ride)
      fwd_R_20    : signed R after 20 bars (close-based)
      hit_2R_first: 1 if price reached +2R before closing below -1R within 40 bars

Then: Spearman IC per feature (full period), IC stability (train<2021 vs test>=2021),
and decile spread for the strongest features (does top-decile monotonically win more?).

IC interpretation (Grinold/Kahn): |IC| 0.03 weak, 0.05 useful, 0.10 strong (for
single-period stock forecasting an IC of 0.05-0.10 is a real, tradable edge).
"""
import sqlite3
import sys
import time
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import load_bars, WARMUP, TRADEABLE, BASE_TAIL  # noqa: E402
from backend.engine.base import analyze_base  # noqa: E402
from backend.engine.fills import DEFAULT_SLIPPAGE, fill_entry  # noqa: E402
from backend.engine.precompute import precompute_features  # noqa: E402
from backend.engine.regime import load_regime  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
FWD = 40   # forward horizon in bars

FEATURES = [
    "trp", "avg_trp", "trp_ratio", "trp_z", "close_position",
    "volume_ratio", "volume_z", "sma_slope_pct", "price_vs_sma_pct",
    "atr_slope_pct", "atr_percentile", "pct_from_52w_high", "ret_126",
    "base_bars", "depth_pct", "prior_advance_pct", "rs", "regime_on",
]

print("Preloading + scanning signals...", flush=True)
t0 = time.time()
regime_map, ret_map = load_regime(CACHE, "NIFTY 500", sma_window=50, slope_lb=5)

con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]

rows = []
for s in symbols:
    bars = load_bars(con, s)
    if len(bars) < 200:
        continue
    df = precompute_features(bars)
    stages = df["stage"].to_numpy()
    contr = df["is_contraction"].to_numpy()
    avgtrp = df["avg_trp"].to_numpy()
    trig = df["trigger_level"].to_numpy()
    ret126 = df["ret_126"].to_numpy()
    cols = {c: df[c].to_numpy() for c in
            ["trp", "avg_trp", "trp_ratio", "trp_z", "close_position", "volume_ratio",
             "volume_z", "sma_slope_pct", "price_vs_sma_pct", "atr_slope_pct",
             "atr_percentile", "pct_from_52w_high", "ret_126"]}

    n = len(bars)
    for i in range(WARMUP, n - 1):
        j = i - 1
        b = bars[i]
        if b.date < START:
            continue
        if not (stages[j] in TRADEABLE and bool(contr[j]) and avgtrp[j] >= 2.0):
            continue
        base = analyze_base(bars[max(0, j - BASE_TAIL + 1): j + 1])
        if not base.is_valid_base:
            continue
        trigger = Decimal(str(round(float(trig[j]), 2)))
        sd = trigger * Decimal(str(round(float(avgtrp[j]), 4))) / Decimal(100)
        if sd <= 0:
            continue
        ent = fill_entry(trigger, b.open, b.high, DEFAULT_SLIPPAGE)
        if ent is None:
            continue

        entry = float(ent)
        stopdist = float(sd)
        fwd = bars[i + 1: i + 1 + FWD]
        if len(fwd) < 20:
            continue

        # forward labels
        mfe_R = max((float(fb.high) - entry) / stopdist for fb in fwd)
        # hit 2R (intraday high) before closing below -1R?
        hit_2R_first = 0
        twoR = entry + 2 * stopdist
        stop = entry - stopdist
        for fb in fwd:
            if float(fb.high) >= twoR:
                hit_2R_first = 1
                break
            if float(fb.close) < stop:
                hit_2R_first = 0
                break
        fwd_R_20 = (float(fwd[19].close) - entry) / stopdist if len(fwd) >= 20 else np.nan

        ir = ret_map.get(bars[j].date)
        sr = ret126[j]
        rs = (sr - ir) if (ir is not None and sr == sr) else np.nan

        rec = {c: float(cols[c][j]) for c in cols}
        rec.update({
            "base_bars": base.base_bars,
            "depth_pct": base.depth_pct,
            "prior_advance_pct": base.prior_advance_pct,
            "rs": rs,
            "regime_on": 1.0 if regime_map.get(bars[j].date, False) else 0.0,
            "mfe_R_40": mfe_R,
            "fwd_R_20": fwd_R_20,
            "hit_2R_first": hit_2R_first,
            "year": b.date.year,
            "entry_date": b.date,
        })
        rows.append(rec)
con.close()

D = pd.DataFrame(rows)
D.to_pickle("/home/user/champion-trader/ic_signals.pkl")   # save early — scan is the expensive part
print(f"  {len(D)} signals collected in {time.time()-t0:.0f}s\n")
print(f"Base rates: hit_2R_first={D['hit_2R_first'].mean():.1%}  "
      f"mean mfe_R_40={D['mfe_R_40'].mean():.2f}  mean fwd_R_20={D['fwd_R_20'].mean():+.2f}\n")

# ── IC table (full period) ───────────────────────────────────────────────────
def ic(frame, feat, label):
    """Spearman = Pearson on ranks (avoids the scipy dependency)."""
    sub = frame[[feat, label]].dropna()
    if len(sub) < 30:
        return np.nan
    return sub[feat].rank().corr(sub[label].rank())  # pearson-on-ranks

print("=" * 76)
print("INFORMATION COEFFICIENT  (Spearman rank corr, feature vs forward outcome)")
print("=" * 76)
print(f"{'feature':20}{'IC:mfe_R_40':>13}{'IC:fwd_R_20':>13}{'IC:hit_2R':>11}{'|IC| rank':>11}")
print("-" * 76)
ic_rows = []
for f in FEATURES:
    a = ic(D, f, "mfe_R_40")
    b_ = ic(D, f, "fwd_R_20")
    c = ic(D, f, "hit_2R_first")
    score = np.nanmean([abs(a), abs(b_), abs(c)])
    ic_rows.append((f, a, b_, c, score))
for f, a, b_, c, score in sorted(ic_rows, key=lambda x: -x[4]):
    print(f"{f:20}{a:>+13.3f}{b_:>+13.3f}{c:>+11.3f}{score:>+11.3f}")

# ── IC stability: train (<2021) vs test (>=2021) ─────────────────────────────
print("\n" + "=" * 76)
print("IC STABILITY  (does the signal hold out-of-sample? label = mfe_R_40)")
print("=" * 76)
train = D[D["year"] < 2021]
test = D[D["year"] >= 2021]
print(f"train n={len(train)}  test n={len(test)}\n")
print(f"{'feature':20}{'IC_train':>11}{'IC_test':>11}{'stable?':>10}")
print("-" * 52)
for f, a, b_, c, score in sorted(ic_rows, key=lambda x: -x[4])[:12]:
    it = ic(train, f, "mfe_R_40")
    ie = ic(test, f, "mfe_R_40")
    stable = "yes" if (it == it and ie == ie and np.sign(it) == np.sign(ie) and abs(ie) > 0.02) else "no"
    print(f"{f:20}{it:>+11.3f}{ie:>+11.3f}{stable:>10}")

# ── Decile spread for the strongest stable features ──────────────────────────
print("\n" + "=" * 76)
print("DECILE SPREAD  (mean mfe_R_40 + hit_2R rate by feature decile, 1=low 10=high)")
print("=" * 76)
top_feats = [f for f, *_ in sorted(ic_rows, key=lambda x: -x[4])[:5]]
for f in top_feats:
    sub = D[[f, "mfe_R_40", "hit_2R_first"]].dropna()
    if len(sub) < 100:
        continue
    sub = sub.copy()
    sub["dec"] = pd.qcut(sub[f].rank(method="first"), 10, labels=False) + 1
    g = sub.groupby("dec").agg(mfe=("mfe_R_40", "mean"), win=("hit_2R_first", "mean"), n=("mfe_R_40", "size"))
    print(f"\n{f}:")
    line_mfe = "  mfe_R: " + " ".join(f"D{d}:{g.loc[d,'mfe']:>5.2f}" for d in g.index)
    line_win = "  win% : " + " ".join(f"D{d}:{g.loc[d,'win']:>4.0%}" for d in g.index)
    print(line_mfe)
    print(line_win)

D.to_pickle("/home/user/champion-trader/ic_signals.pkl")
print("\n(signals saved to ic_signals.pkl for the scoring model)")
