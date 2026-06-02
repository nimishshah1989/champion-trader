"""Walk-forward validation — are the parameters real or overfit?

Parameters were identified on 2016-2026. We now test them on sub-periods
to see if the edge holds year-by-year and across market regimes:
  2017: demonetisation hangover → GST rally
  2018: IL&FS credit crunch, mid-cap crash
  2019: election, liquidity squeeze
  2020: COVID crash + extraordinary V-recovery
  2021: massive bull, new highs
  2022: inflation / rate-hike bear market
  2023: recovery
  2024-25: strong bull, then global uncertainty

If SQN holds above 0.5 in MOST years and stays positive on average,
the edge is real. If it's driven by 1-2 good years only, it's regime-specific.

Configs tested:
  A: chandelier 3x + SMA150/20  [original baseline]
  B: chandelier 3x + SMA50/5    [best risk-adjusted, SQN 1.71 full period]
  C: ladder     + SMA50/5       [methodology exit, SQN 1.22, top-5=5%]
"""
import sqlite3
import sys
import time
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars  # noqa: E402
from backend.engine.backtest import replay_trades, RawTrade          # noqa: E402
from backend.engine.fills import DEFAULT_SLIPPAGE                    # noqa: E402
from backend.engine.precompute import precompute_features            # noqa: E402
from backend.engine.regime import load_regime                        # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"

# ── preload everything once ──────────────────────────────────────────────────
print("Preloading bars + features (once)...", flush=True)
t0 = time.time()
regime_50,  _ = load_regime(CACHE, "NIFTY 500", sma_window=50,  slope_lb=5)
regime_150, _ = load_regime(CACHE, "NIFTY 500", sma_window=150, slope_lb=20)

con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
all_bars, all_df = {}, {}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    all_bars[s] = bs
    all_df[s]   = precompute_features(bs)
con.close()
print(f"  {len(all_bars)} symbols loaded in {time.time()-t0:.0f}s\n")


def run_period(start: date, end: date, exit_mode: str, mult: float, regime_map: dict) -> list[float]:
    """Collect raw trades [start, end], return list of net R-multiples."""
    raw: list[RawTrade] = []
    for s, bs in all_bars.items():
        # truncate bars at end so no entries or exits bleed past the period
        bs_cut = [b for b in bs if b.date <= end]
        if len(bs_cut) < 200:
            continue
        df = all_df[s]
        raw += _fast_simulate(
            s, bs_cut, df,
            exit_mode=exit_mode, target_r=2.0, chandelier_mult=mult,
            slippage=DEFAULT_SLIPPAGE, min_trp=2.0,
            start_date=start, use_regime=True, regime_map=regime_map,
        )
    if not raw:
        return []
    res = replay_trades(raw, starting_capital=Decimal("1000000"), rpt_pct=0.5)
    return res.r_multiples


def sqn(rs):
    from math import sqrt
    from statistics import fmean, pstdev
    n = len(rs)
    if n < 5: return float("nan")
    sd = pstdev(rs)
    return fmean(rs) / sd * sqrt(min(n, 100)) if sd else 0.0

def expR(rs): return sum(rs)/len(rs) if rs else float("nan")
def winR(rs): return sum(1 for r in rs if r > 0)/len(rs) if rs else float("nan")


configs = [
    ("A: chan3x SMA150", "chandelier", 3.0, regime_150),
    ("B: chan3x SMA50 ", "chandelier", 3.0, regime_50),
    ("C: ladder SMA50 ", "ladder",     3.0, regime_50),
]

# ── 1. YEAR-BY-YEAR ──────────────────────────────────────────────────────────
print("=" * 78)
print("1. YEAR-BY-YEAR  (each config run on each calendar year independently)")
print("=" * 78)
years = list(range(2017, 2026))
print(f"\n{'year':<6}", end="")
for name, *_ in configs:
    print(f"  {name:>17}(n/SQN/expR)", end="")
print()
print("-" * 78)

year_results = {name: {} for name, *_ in configs}
for yr in years:
    sd, ed = date(yr, 1, 1), date(yr, 12, 31)
    print(f"{yr:<6}", end="", flush=True)
    for name, mode, mult, rmap in configs:
        rs = run_period(sd, ed, mode, mult, rmap)
        s, e, w = sqn(rs), expR(rs), winR(rs)
        year_results[name][yr] = (len(rs), s, e)
        tag = "  " if not (s != s) and s >= 0.5 else "▼ " if not (s != s) else "  "
        print(f"  {tag}{len(rs):>3}t {s:>+5.2f}SQN {e:>+.3f}R", end="", flush=True)
    print()

# summary row
print("-" * 78)
print(f"{'MEAN':<6}", end="")
for name, *_ in configs:
    vals = [(n, s, e) for yr, (n, s, e) in year_results[name].items() if s == s]
    ms = sum(s for _, s, _ in vals)/len(vals) if vals else 0
    me = sum(e for _, _, e in vals)/len(vals) if vals else 0
    mt = sum(n for n, _, _ in vals)//len(vals) if vals else 0
    print(f"  {'':2}{mt:>3}t {ms:>+5.2f}SQN {me:>+.3f}R", end="")
print()


# ── 2. 3-BLOCK SPLIT ─────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print("2. THREE-BLOCK SPLIT  (equal ~3-year blocks, strict holdout)")
print("=" * 78)
blocks = [
    ("2016-2018  bull-dip-bull",  date(2016,4,7),  date(2018,12,31)),
    ("2019-2021  crisis+recovery",date(2019,1,1),  date(2021,12,31)),
    ("2022-2026  bear+rally",     date(2022,1,1),  date(2026,5,31)),
]
hdr = f"{'block':26}{'config':22}{'trades':>7}{'win':>7}{'expR':>8}{'SQN':>7}"
print(hdr)
print("-" * len(hdr))
for blabel, sd, ed in blocks:
    first = True
    for name, mode, mult, rmap in configs:
        rs = run_period(sd, ed, mode, mult, rmap)
        s, e, w = sqn(rs), expR(rs), winR(rs)
        bl = blabel if first else ""
        print(f"{bl:26}{name:22}{len(rs):>7}{w:>7.1%}{e:>+8.3f}{s:>7.2f}")
        first = False
    print()

print("SQN guide: >1.5 excellent  >1.0 good  >0.5 ok  <0 edge not present in this period")
print("If SQN holds above 0.5 in most periods → parameters are real, not overfit.")
