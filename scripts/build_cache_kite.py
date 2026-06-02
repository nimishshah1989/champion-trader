"""Rebuild the OHLCV cache from KITE (fully split+bonus adjusted) -> SQLite.

WHY: the Atlas de_equity_ohlcv columns are only partially adjusted -- bonuses
post-2019 are fixed, but SPLITS (null ratios in de_corporate_actions) and ALL
pre-2020 actions are still RAW, manufacturing phantom -20R "gap" losses in the
backtest. Kite's historical API returns broker-adjusted prices across all years
AND is the exact source we trade on live, so backtest == reality.

Resumable (`done` table), commits per symbol, ~1800-day windows (Kite caps 'day'
at 2000), polite throttle + exponential backoff on rate-limit/network errors.
Index bars (NIFTY 50/500) need no adjustment and are copied from the old cache.
Builds to champion_cache_kite.sqlite; swap in after validation.

The windowed fetch + schema live in backend.engine.market_store (the live daily ingest,
scripts/ingest_kite_daily.py, shares the same code — one implementation).
"""
import json
import sqlite3
import sys
from datetime import date

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine import market_store                     # noqa: E402
from backend.engine.kite_data import KiteHistoricalAdapter  # noqa: E402

ROOT = "/home/user/champion-trader"
OLD = f"{ROOT}/champion_cache.sqlite"
CACHE = f"{ROOT}/champion_cache_kite.sqlite"
START, END = date(2015, 1, 1), date.today()

env = {}
for line in open(f"{ROOT}/.env"):
    s = line.strip()
    if "=" in s and not s.startswith("#"):
        k, v = s.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")

ad = KiteHistoricalAdapter(env["KITE_API_KEY"], env["KITE_ACCESS_TOKEN"])
universe = json.load(open(f"{ROOT}/backend/data/atlas_universe.json"))["symbols"]


def fetch_symbol(sym):
    """Full history across ~1800-day windows, deduped by date (market_store.fetch_history)."""
    return market_store.fetch_history(ad, sym, START, END)


con = sqlite3.connect(CACHE)
market_store.ensure_schema(con)

# indices carry no split/bonus -> copy straight from the old cache
if con.execute("select count(*) from index_bars").fetchone()[0] == 0:
    try:
        old = sqlite3.connect(OLD)
        rows = old.execute("select index_code,date,close from index_bars").fetchall()
        old.close()
        con.executemany("insert or replace into index_bars values(?,?,?)", rows)
        con.commit()
        print(f"copied {len(rows)} index bars from old cache", flush=True)
    except Exception as e:
        print(f"index copy skipped: {e}", flush=True)

done = {r[0] for r in con.execute("select symbol from done")}
total = len(universe)
print(f"KITE cache build: {total} symbols, {len(done)} already done, {START}..{END}", flush=True)

missing, failed = 0, 0
for i, sym in enumerate(universe):
    if sym in done:
        continue
    try:
        bars = fetch_symbol(sym)
        market_store.upsert_bars(con, sym, bars)
        con.execute("insert or replace into done values(?,?)", (sym, len(bars)))
        con.commit()
    except KeyError:
        con.execute("insert or replace into done values(?,?)", (sym, 0))  # not in Kite -> skip on resume
        con.commit()
        missing += 1
    except Exception as exc:
        print(f"FAIL {sym}: {type(exc).__name__} {str(exc)[:120]}", flush=True)
        failed += 1
    if (i + 1) % 50 == 0:
        ns, nr = con.execute("select count(*), coalesce(sum(n),0) from done").fetchone()
        print(f"  {i + 1}/{total}  done={ns} bars={nr:,} missing={missing} failed={failed}", flush=True)

n_sym, n_rows = con.execute("select count(*), coalesce(sum(n),0) from done where n>0").fetchone()
print(f"KITE CACHE COMPLETE: {n_sym} symbols with data, {n_rows:,} bars, "
      f"{missing} not-in-kite, {failed} failed -> {CACHE}", flush=True)
con.close()
