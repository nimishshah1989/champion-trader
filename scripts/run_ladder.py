"""Champion R-ladder exit (the ACTUAL methodology exit) vs the chandelier trail.

The ladder books 20% at 2R (stop->breakeven), then 20%/40%/80% of the REMAINDER
at 4R/8R/12R, trailing the stop up to 0R/+2R/+4R/+8R. Every trade therefore
closes on its (rising) stop. The discrete outcomes are ~ -1R (failed before 2R),
+0.40R (popped to 2R then faded to breakeven), +2.32R, +4.62R, +7.39R.

This is the robustness test the user demanded: NOT "two trades at 10% win rate"
carrying everything. We report median R and the share of gross profit from the
top-5 trades -- if a handful of trades make all the money, the edge is a mirage.

Per-trade R stats (win%/expectancy/SQN/median/top-5%) are portfolio-independent
and trustworthy. Final equity / Calmar from the sequential per-trade replay are
NOT a real concurrent portfolio -- treated as indicative only, pending R-4.
"""
import sys
import time
from datetime import date
from statistics import median

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import run_universe_backtest  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)


def robustness(rs: list[float]) -> tuple[float, float, float]:
    """median R, share of GROSS PROFIT from the top-5 winners, share from top-1%."""
    if not rs:
        return 0.0, 0.0, 0.0
    wins = sorted((r for r in rs if r > 0), reverse=True)
    gross = sum(wins)
    if gross <= 0:
        return median(rs), 0.0, 0.0
    top5 = sum(wins[:5]) / gross
    k = max(1, len(wins) // 100)
    top1pct = sum(wins[:k]) / gross
    return median(rs), top5, top1pct


def hist(rs: list[float]) -> str:
    """Bucket the discrete ladder outcomes so we can see the profile."""
    buckets = [
        ("<=-1R", lambda r: r <= -0.9),
        ("-0.9..0", lambda r: -0.9 < r <= 0.0),
        ("0..1R", lambda r: 0.0 < r <= 1.0),
        ("1..3R", lambda r: 1.0 < r <= 3.0),
        ("3..6R", lambda r: 3.0 < r <= 6.0),
        (">6R", lambda r: r > 6.0),
    ]
    n = len(rs) or 1
    return "  ".join(f"{name}:{sum(1 for r in rs if fn(r)):>4}({sum(1 for r in rs if fn(r))/n:>4.0%})"
                     for name, fn in buckets)


configs = [
    ("ladder  (no filters)",   dict(exit_mode="ladder")),
    ("ladder  + regime",       dict(exit_mode="ladder", use_regime=True)),
    ("chandelier 3x + regime", dict(exit_mode="chandelier", chandelier_mult=3.0, use_regime=True)),
]

print("Champion R-ladder vs chandelier  (RPT 0.5%, after costs, 2016-2026)\n")
hdr = (f"{'config':24}{'trades':>7}{'win':>7}{'avgWinR':>9}{'avgLossR':>9}"
       f"{'medR':>7}{'expR':>8}{'SQN':>7}{'top5%':>7}{'finalEq':>13}")
print(hdr)
print("-" * len(hdr))
rows = []
for name, kw in configs:
    t = time.time()
    res, used = run_universe_backtest(CACHE, start_date=START, **kw)
    dt = time.time() - t
    rs = res.r_multiples
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    med, top5, _ = robustness(rs)
    print(f"{name:24}{res.num_trades:>7}{res.win_rate:>7.1%}{aw:>9.2f}{al:>9.2f}"
          f"{med:>7.2f}{res.expectancy:>+8.3f}{res.sqn:>7.2f}{top5:>7.0%}"
          f"{res.final_equity:>13,.0f}  ({dt:.0f}s, {used} syms)")
    rows.append((name, rs))

print("\nR-distribution (the shape of the edge):")
for name, rs in rows:
    print(f"  {name:24} {hist(rs)}")

print("\nBenchmark to beat:  NIFTY 500 buy-and-hold ~ 13.4%/yr, Calmar ~0.30")
print("Edge verdict reads off expectancy/SQN/median/top5% -- NOT finalEq (sequential replay, not a concurrent portfolio).")
