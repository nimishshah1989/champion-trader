"""Daily Kite ingest (the repurposed corpus_updater job): refresh bars + index_bars.

Incrementally pulls Kite's adjusted daily OHLCV for the universe and the NIFTY indices
into the market store the engine reads (``backtest_fast.load_bars`` / ``regime.load_regime``).
This is the SAME adjusted feed the backtest used, so live signals == backtest signals.
Run after the market close.

Resumable & incremental: each symbol fetches only bars after its last stored date, so a
daily run is cheap. Needs KITE_API_KEY / KITE_ACCESS_TOKEN in .env (the access token is
refreshed daily via the Kite login flow).

    python scripts/ingest_kite_daily.py [--cache PATH] [--start YYYY-MM-DD]
"""
import argparse
import sqlite3
import sys
from datetime import date

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine import market_store                      # noqa: E402
from backend.engine.kite_data import KiteHistoricalAdapter   # noqa: E402

ROOT = "/home/user/champion-trader"
DEFAULT_CACHE = f"{ROOT}/champion_cache.sqlite"
INDICES = ["NIFTY 50", "NIFTY 500"]


def _load_env() -> dict[str, str]:
    env = {}
    for line in open(f"{ROOT}/.env"):
        s = line.strip()
        if "=" in s and not s.startswith("#"):
            k, v = s.split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
    return env


def _universe(con: sqlite3.Connection) -> list[str]:
    """Symbols already tracked (done.n>0); fall back to the bundled universe file."""
    rows = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
    if rows:
        return rows
    import json
    return json.load(open(f"{ROOT}/backend/data/atlas_universe.json"))["symbols"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--start", default="2015-01-01", help="backfill start for brand-new symbols")
    args = ap.parse_args()
    start, today = date.fromisoformat(args.start), date.today()

    env = _load_env()
    adapter = KiteHistoricalAdapter(env["KITE_API_KEY"], env["KITE_ACCESS_TOKEN"])
    con = sqlite3.connect(args.cache)
    market_store.ensure_schema(con)

    symbols = _universe(con)
    print(f"Kite ingest -> {args.cache}: {len(symbols)} symbols + {len(INDICES)} indices, as-of {today}", flush=True)

    new_bars = missing = failed = 0
    for i, sym in enumerate(symbols):
        try:
            new_bars += market_store.ingest_symbol(con, adapter, sym, start=start, end=today, as_of=today)
        except KeyError:
            con.execute("insert or replace into done values(?,?)", (sym, 0))  # not in Kite -> skip on resume
            con.commit()
            missing += 1
        except Exception as exc:
            print(f"FAIL {sym}: {type(exc).__name__} {str(exc)[:120]}", flush=True)
            failed += 1
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(symbols)}  new_bars={new_bars:,} missing={missing} failed={failed}", flush=True)

    for code in INDICES:
        try:
            n = market_store.ingest_index(con, adapter, code, start=start, end=today, as_of=today)
            print(f"  index {code}: +{n} closes", flush=True)
        except Exception as exc:
            print(f"FAIL index {code}: {type(exc).__name__} {str(exc)[:120]}", flush=True)

    con.close()
    print(f"DONE: +{new_bars:,} new equity bars, {missing} not-in-kite, {failed} failed.", flush=True)


if __name__ == "__main__":
    main()
