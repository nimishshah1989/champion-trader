"""CAP / LIQUIDITY-TIER DIAGNOSTIC for v2 — measure before tuning.

Question: does the validated v2 edge work EQUALLY across cap tiers under the SAME
fixed thresholds? Take the v2 trades, tag each with the stock's liquidity AT ENTRY
(median daily turnover = close*volume over the prior 60 bars — our cap proxy, since
shares-outstanding isn't in the cache), bucket mega->micro, and measure per-trade
expectancy (win%, meanR) + profit contribution + the volume/TRP behaviour per tier.

Read:
  * win%/meanR ~flat across tiers      -> fixed thresholds generalise; cap-logic = overfit risk.
  * degrade toward mega (or mega/large nearly absent) -> evidence for cap-aware floors.
  * avgTRP rising toward micro          -> confirms the min-TRP>=2 floor is implicitly cap-tilted.

Diagnostic only — no parameters are changed. Turnover is a LIQUIDITY proxy for cap
(correlated with, not identical to, free-float market cap).
"""
import sqlite3
import sys
import warnings
from datetime import date
from decimal import Decimal
from statistics import mean, median

warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars   # noqa: E402
from backend.engine.precompute import precompute_features            # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
CR = 1e7   # 1 crore in rupees


def slip(a):
    return Decimal("0.0010") if a >= 15 else Decimal("0.0025") if a >= 5 else Decimal("0.0050") if a >= 1 else Decimal("0.0100")


# turnover bands (Rs cr/day) -> cap-tier proxy
TIERS = [
    ("mega  (>=100cr)", lambda t: t >= 100),
    ("large (25-100cr)", lambda t: 25 <= t < 100),
    ("mid   (5-25cr)", lambda t: 5 <= t < 25),
    ("small (1-5cr)", lambda t: 1 <= t < 5),
    ("micro (<1cr)", lambda t: t < 1),
]

con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
recs = []   # (turnover_cr_at_entry, R, vol_ratio, avg_trp, year)
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    tnv_all = sorted(float(b.close) * b.volume for b in bs[-1000:])
    adt = median(tnv_all) / CR if tnv_all else 0
    vsma50 = df["vol_sma50"].to_numpy()
    avgtrp = df["avg_trp"].to_numpy()
    idx_of = {b.date: i for i, b in enumerate(bs)}
    tr = _fast_simulate(s, bs, df, exit_mode="chandelier", target_r=2.0, chandelier_mult=5.0,
                        slippage=slip(adt), min_trp=2.0, start_date=START, use_regime=False,
                        skip_circuit_locked=True, vol_breakout_k=2.0)
    for t in tr:
        i = idx_of[t.entry_date]
        win = [float(bs[k].close) * bs[k].volume for k in range(max(0, i - 60), i)]
        turn_cr = (median(win) / CR) if win else adt           # liquidity at trade time
        R = float((t.exit - t.entry) / t.stopdist)
        v50 = vsma50[i]
        vr = (bs[i].volume / v50) if (v50 == v50 and v50 > 0) else float("nan")
        recs.append((turn_cr, R, vr, float(avgtrp[i - 1]), t.entry_date.year))
con.close()

n = len(recs)
tot = sum(r[1] for r in recs)
print(f"{n} v2 trades tagged with entry-time liquidity (turnover = cap proxy)")
print(f"total profit = {tot:+.0f}R\n")


def stats(rows):
    if not rows:
        return (0, 0.0, 0.0, 0.0, 0.0)
    rs = [r[1] for r in rows]
    return (len(rows), sum(1 for r in rs if r > 0) / len(rs), mean(rs), median(rs), sum(rs))


print("BY CAP TIER (turnover band):")
print(f"{'tier':18}{'n':>4}{'%trd':>6}{'win%':>6}{'meanR':>7}{'medR':>7}{'sumR':>7}{'%prof':>7}{'avgVR':>7}{'avgTRP':>7}")
print("-" * 88)
for name, f in TIERS:
    rows = [r for r in recs if f(r[0])]
    nn, w, mr, mdr, sr = stats(rows)
    if nn == 0:
        print(f"{name:18}{0:>4}")
        continue
    avgvr = mean([r[2] for r in rows if r[2] == r[2]]) if any(r[2] == r[2] for r in rows) else float("nan")
    avgtrp_ = mean([r[3] for r in rows if r[3] == r[3]])
    print(f"{name:18}{nn:>4}{nn/n:>6.0%}{w:>6.0%}{mr:>+7.2f}{mdr:>+7.2f}{sr:>+7.0f}{sr/tot:>7.0%}{avgvr:>7.1f}{avgtrp_:>7.1f}")
print("-" * 88)

# equal-count quintiles (each ~20% of trades) — robust to uneven band counts
srt = sorted(recs, key=lambda r: r[0])
q = len(srt) // 5
print("\nEQUAL-COUNT QUINTILES by turnover (low -> high liquidity, each ~20% of trades):")
print(f"{'quintile':10}{'turnover range (cr)':>22}{'n':>5}{'win%':>6}{'meanR':>7}{'sumR':>7}{'%prof':>7}")
for k in range(5):
    rows = srt[k * q:(k + 1) * q] if k < 4 else srt[k * q:]
    nn, w, mr, mdr, sr = stats(rows)
    rng = f"{rows[0][0]:.2f} - {rows[-1][0]:.1f}"
    print(f"Q{k+1:<9}{rng:>22}{nn:>5}{w:>6.0%}{mr:>+7.2f}{sr:>+7.0f}{sr/tot:>7.0%}")

print("\nReading guide:")
print("  flat win%/meanR across tiers      -> fixed thresholds generalise; cap-logic adds overfit risk")
print("  degrade toward mega (or mega/large nearly absent) -> evidence for cap-aware thresholds")
print("  avgTRP rising toward micro          -> the min-TRP>=2 floor is implicitly cap-tilted")
