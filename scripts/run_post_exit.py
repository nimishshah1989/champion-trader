"""Post-exit trajectory analysis.

For every trade in ladder+regime, look at what price does in the 5/10/20/40
bars AFTER we exit. This answers: are we cutting winners short, or are our
stop-outs at the actual bottom?

Two classes:
  - STOPPED (exit R <= 0): did price bounce ABOVE our stop within N bars?
    If yes = premature stop, trend wasn't over.
  - PARTIALS/TOPS (exit R > 0): how much more did the stock run after we fully
    exited? R left on table = peak close in next N bars vs our exit level.

We also track the "continuation rate" per rung — of trades that hit rung k,
what fraction went on to hit rung k+1? This tells us where the edge lives.
"""
import sqlite3
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars, LADDER  # noqa: E402
from backend.engine.fills import DEFAULT_SLIPPAGE  # noqa: E402
from backend.engine.precompute import precompute_features  # noqa: E402
from backend.engine.regime import load_regime  # noqa: E402
from backend.engine.kite_data import Bar  # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)


def _simulate_with_detail(symbol, bars, df, regime_map):
    """Like _fast_simulate ladder+regime but also records the exit_bar_idx
    and whether each LADDER rung was reached, so we can do post-exit analysis."""
    from backend.engine.backtest_fast import WARMUP, TRADEABLE, BASE_TAIL
    from backend.engine.base import analyze_base
    from backend.engine.fills import fill_entry, fill_stop

    stages = df["stage"].to_numpy()
    contr  = df["is_contraction"].to_numpy()
    avgtrp = df["avg_trp"].to_numpy()
    trig   = df["trigger_level"].to_numpy()
    atr_v  = df["atr"].to_numpy()
    cm_mult = Decimal("3")

    records = []   # (raw_r_gross, rungs_hit, exit_bar_idx, entry_bar_idx, entry, stop, stopdist)
    long = False
    entry = stop = stopdist = hh = Decimal(0)
    entry_date = entry_idx = None
    realized_r = remaining = Decimal(0)
    lvl_idx = rungs_hit = 0

    for i in range(WARMUP, len(bars)):
        b = bars[i]
        if long:
            if b.low <= stop:
                fp = fill_stop(stop, b.open, b.low, DEFAULT_SLIPPAGE)
                rem_r = (fp - entry) / stopdist
                total_r = realized_r + remaining * rem_r
                records.append((float(total_r), rungs_hit, i, entry_idx,
                                 float(entry), float(stop), float(stopdist)))
                long = False
            else:
                while lvl_idx < len(LADDER) and b.high >= entry + Decimal(str(LADDER[lvl_idx][0])) * stopdist:
                    lvl_r, frac, stop_after = LADDER[lvl_idx]
                    realized_r += Decimal(str(frac)) * Decimal(str(lvl_r))
                    remaining  -= Decimal(str(frac))
                    stop = entry + Decimal(str(stop_after)) * stopdist
                    rungs_hit = lvl_idx + 1
                    lvl_idx += 1
            continue

        if b.date < START:
            continue
        j = i - 1
        if not (stages[j] in TRADEABLE and bool(contr[j]) and avgtrp[j] >= 2.0):
            continue
        if not (regime_map or {}).get(bars[j].date, False):
            continue
        if not analyze_base(bars[max(0, j - BASE_TAIL + 1): j + 1]).is_valid_base:
            continue
        trigger = Decimal(str(round(float(trig[j]), 2)))
        sd = trigger * Decimal(str(round(float(avgtrp[j]), 4))) / Decimal(100)
        if sd > 0:
            ent = fill_entry(trigger, b.open, b.high, DEFAULT_SLIPPAGE)
            if ent is not None:
                entry, stopdist = ent, sd
                stop = ent - sd
                hh = b.high
                entry_date = b.date
                entry_idx = i
                realized_r, remaining, lvl_idx, rungs_hit = Decimal(0), Decimal(1), 0, 0
                long = True
    return records


print("Loading data...", flush=True)
regime_map, _ = load_regime(CACHE, "NIFTY 500")
con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]

all_records = []
bars_map = {}
for s in symbols:
    bs = load_bars(con, s)
    if len(bs) < 200:
        continue
    df = precompute_features(bs)
    recs = _simulate_with_detail(s, bs, df, regime_map)
    for rec in recs:
        all_records.append((s, bs, rec))
    if len(bs) > 0:
        bars_map[s] = bs
con.close()

print(f"Analysing {len(all_records)} trades...\n")

# --- 1. STOP-OUT analysis: did price bounce after our stop? ---
HORIZONS = [5, 10, 20, 40]
stop_bounce = {h: 0 for h in HORIZONS}
stop_bounce_r = {h: [] for h in HORIZONS}
stopped = 0

# --- 2. WINNER analysis: R left on table ---
winner_left = {h: [] for h in HORIZONS}
winners = 0

# --- 3. Rung continuation rates ---
rung_start  = [0] * (len(LADDER) + 1)   # n trades that entered rung k
rung_hit    = [0] * (len(LADDER) + 1)   # n that actually reached rung k

rung_start[0] = len(all_records)

for sym, bars, (r, rungs, exit_i, entry_i, entry, stop_price, stopdist) in all_records:
    # rung continuation
    for k in range(len(LADDER)):
        if rungs >= k:
            rung_start[k] += (1 if k > 0 else 0)
        if rungs > k:
            rung_hit[k] += 1

    future = bars[exit_i + 1: exit_i + 1 + max(HORIZONS)]
    if not future:
        continue

    if r <= 0:
        stopped += 1
        for h in HORIZONS:
            slice_ = future[:h]
            peak_close = max((float(b.close) for b in slice_), default=float(bars[exit_i].close))
            exit_price = entry + r * stopdist   # approx synthetic exit level
            if peak_close > (stop_price * 1.01):   # bounced >1% above our stop
                stop_bounce[h] += 1
            r_recovery = (peak_close - (entry + r * stopdist)) / stopdist
            stop_bounce_r[h].append(r_recovery)
    else:
        winners += 1
        exit_price = entry + r * stopdist
        for h in HORIZONS:
            slice_ = future[:h]
            peak_close = max((float(b.close) for b in slice_), default=float(exit_price))
            r_left = (peak_close - exit_price) / stopdist
            winner_left[h].append(r_left)

print("=" * 70)
print("1. STOP-OUT QUALITY  (did price BOUNCE after our stop?)")
print(f"   Total stop-outs: {stopped}")
for h in HORIZONS:
    n = stop_bounce[h]
    avg = sum(stop_bounce_r[h]) / len(stop_bounce_r[h]) if stop_bounce_r[h] else 0
    print(f"   {h:>2}bars later: price >1% above stop in {n:>3}/{stopped} ({n/stopped:>4.0%}) cases  avg recovery: +{avg:.2f}R")

print()
print("2. WINNER EXIT QUALITY  (R left on table after our final exit)")
print(f"   Total winners: {winners}")
for h in HORIZONS:
    vals = winner_left[h]
    avg = sum(vals) / len(vals) if vals else 0
    pos = sum(1 for v in vals if v > 0.5)
    print(f"   {h:>2}bars later: avg +{avg:.2f}R more available; price ran >0.5R further in {pos}/{winners} ({pos/winners:>4.0%}) trades")

print()
print("3. RUNG CONTINUATION RATES  (where does the cascade die?)")
rung_start[0] = len(all_records)
for k in range(len(LADDER)):
    hits_k = sum(1 for _, _, (r, rungs, *_) in all_records if rungs > k)
    pct = hits_k / len(all_records)
    level = LADDER[k][0]
    print(f"   Reached {level}R rung: {hits_k:>4}/{len(all_records)} ({pct:>5.1%})")

print()
print("4. R DISTRIBUTION BY EXIT TYPE")
full_exits = [(r, rungs) for _, _, (r, rungs, *_) in all_records if rungs == len(LADDER)]
partial_exits = [(r, rungs) for _, _, (r, rungs, *_) in all_records if 0 < rungs < len(LADDER)]
pure_stops = [(r, rungs) for _, _, (r, rungs, *_) in all_records if rungs == 0]

def fmt(lst):
    rs = [r for r, _ in lst]
    if not rs: return "n=0"
    return f"n={len(rs):>4}  avg={sum(rs)/len(rs):>+.2f}R"

print(f"   Pure stop (0 rungs hit):       {fmt(pure_stops)}")
print(f"   Partial (1-3 rungs):           {fmt(partial_exits)}")
print(f"   Full ladder (all 4 rungs hit): {fmt(full_exits)}")
