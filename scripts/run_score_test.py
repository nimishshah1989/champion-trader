"""Composite alpha score — can we SELECT better setups within the regime-on universe?

Individual feature ICs are weak (0.03-0.08), but combining stable, roughly
independent weak signals can lift the composite IC. We build an IC-signed,
z-scored composite from the features that were STABLE train->test:
    depth_pct(-)  avg_trp(-)  prior_advance_pct(+)  trp(-)  sma_slope_pct(+)
(regime_on is the GATE, not a ranker, so it's excluded from selection.)

Honest protocol:
  - z-score params + signs fit on TRAIN (entry_date < 2021), regime-on only
  - applied BLIND to TEST (>= 2021), regime-on only
  - quartile analysis: do top-score setups have higher hit_2R / fwd_R / mfe?
If top quartile barely beats bottom, selection adds little (weak IC confirmed)
and we focus elsewhere. If it separates cleanly, we wire it into the engine.
"""
import sys
import numpy as np
import pandas as pd

D = pd.read_pickle("/home/user/champion-trader/ic_signals.pkl")
D = D[D["regime_on"] == 1.0].copy()            # the universe we actually trade
train = D[D["year"] < 2021].copy()
test = D[D["year"] >= 2021].copy()
print(f"regime-on signals: train={len(train)}  test={len(test)}\n")

# IC-signed, z-scored composite (params from TRAIN only)
FEATS = {"depth_pct": -1, "avg_trp": -1, "prior_advance_pct": +1, "trp": -1, "sma_slope_pct": +1}
mu = {f: train[f].mean() for f in FEATS}
sd = {f: train[f].std() or 1.0 for f in FEATS}

def score(frame):
    s = np.zeros(len(frame))
    for f, sign in FEATS.items():
        s += sign * ((frame[f].values - mu[f]) / sd[f])
    return s

train["score"] = score(train)
test["score"] = score(test)

def quartile_table(frame, label):
    frame = frame.copy()
    frame["q"] = pd.qcut(frame["score"].rank(method="first"), 4, labels=[1, 2, 3, 4])
    g = frame.groupby("q", observed=True).agg(
        n=("score", "size"),
        hit2R=("hit_2R_first", "mean"),
        fwdR20=("fwd_R_20", "mean"),
        mfeR=("mfe_R_40", "mean"),
    )
    print(f"{label}")
    print(f"  {'quartile':>9}{'n':>6}{'hit_2R':>9}{'fwd_R_20':>10}{'mfe_R_40':>10}")
    for q in g.index:
        print(f"  {('Q'+str(q)):>9}{int(g.loc[q,'n']):>6}{g.loc[q,'hit2R']:>9.1%}"
              f"{g.loc[q,'fwdR20']:>+10.2f}{g.loc[q,'mfeR']:>10.2f}")
    spread = g.loc[4, "hit2R"] - g.loc[1, "hit2R"]
    print(f"  Q4-Q1 hit_2R spread: {spread:+.1%}\n")
    return spread

print("=" * 60)
print("IN-SAMPLE (train 2016-2020) — sanity check the score orders correctly")
print("=" * 60)
quartile_table(train, "TRAIN")

print("=" * 60)
print("OUT-OF-SAMPLE (test 2021-2026) — the honest test")
print("=" * 60)
oos = quartile_table(test, "TEST")

# composite IC out-of-sample
ic_oos = test["score"].rank().corr(test["mfe_R_40"].rank())
ic_hit = test["score"].rank().corr(test["hit_2R_first"].rank())
print(f"Composite IC (OOS): vs mfe_R_40 = {ic_oos:+.3f}   vs hit_2R = {ic_hit:+.3f}")
print("\nVerdict: a Q4-Q1 hit_2R spread > ~8% OOS = selection is worth wiring in.")
print("         < ~4% = weak IC confirmed, selection won't move the needle much.")
