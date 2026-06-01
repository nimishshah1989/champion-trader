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
"""
import json
import sqlite3
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.kite_data import KiteHistoricalAdapter  # noqa: E402

ROOT = "/home/user/champion-trader"
OLD = f"{ROOT}/champion_cache.sqlite"
CACHE = f"{ROOT}/champion_cache_kite.sqlite"
START, END = date(2015, 1, 1), date.today()
WINDOW = 1800          # < Kite's 2000-day cap for daily candles
THROTTLE = 0.35        # ~2.8 req/s, under the 3 req/s historical limit

env = {}
for line in open(f"{ROOT}/.env"):
    s = line.strip()
    if "=" in s and not s.startswith("#"):
        k, v = s.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")

ad = KiteHistoricalAdapter(env["KITE_API_KEY"], env["KITE_ACCESS_TOKEN"])
universe = json.load(open(f"{ROOT}/backend/data/atlas_universe.json"))["symbols"]


def fetch_with_retry(sym, a, b):
    """One window with up to 4 backoff retries on transient (network/429) errors."""
    delay = 2.0
    for attempt in range(5):
        try:
            return ad.daily_bars(sym, a, b)
        except KeyError:
            raise                       # symbol not in Kite -> not transient
        except Exception:
            if attempt == 4:
                raise
            time.sleep(delay)
            delay *= 2
    return []


def fetch_symbol(sym):
    """Full history across ~1800-day windows, deduped by date."""
    by_date = {}
    a = START
    while a <= END:
        b = min(a + timedelta(days=WINDOW), END)
        for bar in fetch_with_retry(sym, a, b):
            by_date[bar.date] = bar
        time.sleep(THROTTLE)
        a = b + timedelta(days=1)
    return [by_date[d] for d in sorted(by_date)]


con = sqlite3.connect(CACHE)
con.execute(
    "create table if not exists bars(symbol text, date text, open text, high text, "
    "low text, close text, volume integer, delivery_pct real, primary key(symbol,date))"
)
con.execute("create table if not exists done(symbol text primary key, n integer)")
con.execute("create table if not exists index_bars(index_code text, date text, close real, primary key(index_code,date))")
con.commit()

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
        con.executemany(
            "insert or replace into bars values(?,?,?,?,?,?,?,?)",
            [(sym, b.date.isoformat(), str(b.open), str(b.high), str(b.low),
              str(b.close), b.volume, None) for b in bars],
        )
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
