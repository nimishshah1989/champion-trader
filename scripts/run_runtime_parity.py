"""PHASE 0 PARITY GATE — prove the extracted runtime == validated backtest, trade-for-trade.

Runs, on a sample of symbols:
  (A) the validated engine: backtest_fast._fast_simulate v2
      (chandelier 5xATR, vol_breakout_k=2.0, skip_circuit_locked, min_trp=2.0)
  (B) the extracted runtime: signal_service.entry_at + exit_service.step driven by the
      SAME precomputed features.
and asserts identical trade lists (entry_date, exit_date, entry, exit, stopdist).

If this is green, the runtime IS the validated v2 — the live app can be wired to it.

    python scripts/run_runtime_parity.py [N_symbols]   # default 150; 0 = all
"""
import sqlite3
import sys
import warnings
from datetime import date
from decimal import Decimal
from statistics import median

warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.backtest_fast import _fast_simulate, load_bars            # noqa: E402
from backend.engine.precompute import precompute_features                     # noqa: E402
from backend.engine.runtime import exit_service, signal_service              # noqa: E402
from backend.engine.runtime.config import STRATEGY_V2                         # noqa: E402
from backend.engine.runtime.signal_service import WARMUP, context_from_df    # noqa: E402

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
START = date(2016, 4, 7)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150


def slip(a):
    return Decimal("0.0010") if a >= 15 else Decimal("0.0025") if a >= 5 else Decimal("0.0050") if a >= 1 else Decimal("0.0100")


def runtime_sim(bars, df, slippage):
    """Drive the extracted runtime over one symbol, mirroring the engine's FLAT/LONG loop."""
    ctx = context_from_df(bars, df)
    atr = df["atr"].to_numpy()
    out, long, trail = [], False, None
    entry = stopdist = None
    entry_date = None
    for i in range(WARMUP, len(bars)):
        b = bars[i]
        if long:
            dec = exit_service.step(trail, b, atr[i], slippage)
            if dec.exited:
                out.append((entry_date, b.date, entry, dec.fill_price, stopdist))
                long = False
            continue
        if b.date < START:
            continue
        sig = signal_service.entry_at(ctx, i, params=STRATEGY_V2, slippage=slippage)
        if sig is None:
            continue
        entry, stopdist, entry_date = sig.entry, sig.stopdist, b.date
        trail = exit_service.init_trail(entry, stopdist, b.high)
        long = True
    return out


con = sqlite3.connect(CACHE)
symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
if N > 0:
    symbols = symbols[:N]

checked = total_trades = mismatch_symbols = 0
first_diff = None
for s in symbols:
    bars = load_bars(con, s)
    if len(bars) < 200:
        continue
    df = precompute_features(bars)
    tnv = sorted(float(b.close) * b.volume for b in bars[-1000:])
    sl = slip(median(tnv) / 1e7 if tnv else 0)
    eng = _fast_simulate(s, bars, df, exit_mode="chandelier", target_r=2.0,
                         chandelier_mult=float(STRATEGY_V2.chandelier_mult), slippage=sl,
                         min_trp=STRATEGY_V2.min_trp, start_date=START, use_regime=False,
                         skip_circuit_locked=STRATEGY_V2.skip_circuit_locked,
                         vol_breakout_k=STRATEGY_V2.vol_breakout_k)
    rt = runtime_sim(bars, df, sl)
    checked += 1
    eng_t = [(t.entry_date, t.exit_date, t.entry, t.exit, t.stopdist) for t in eng]
    total_trades += len(eng_t)
    if eng_t != rt:
        mismatch_symbols += 1
        if first_diff is None:
            for a, b_ in zip(eng_t, rt):
                if a != b_:
                    first_diff = (s, a, b_)
                    break
            else:
                first_diff = (s, f"len engine={len(eng_t)}", f"len runtime={len(rt)}")
con.close()

print(f"symbols checked : {checked}")
print(f"v2 trades (engine): {total_trades}")
print(f"symbols mismatching: {mismatch_symbols}")
if first_diff:
    print(f"first diff @ {first_diff[0]}:\n  engine : {first_diff[1]}\n  runtime: {first_diff[2]}")
print("\nPARITY: PASS  (runtime == validated v2)" if mismatch_symbols == 0 else "\nPARITY: FAIL")
sys.exit(0 if mismatch_symbols == 0 else 1)
