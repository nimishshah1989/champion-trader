"""One-time bulk pull: the full universe's OHLCV from Atlas -> local SQLite cache.

Resumable (skips symbols already done), commits per symbol, retries are handled
inside the adapter. The calibration then runs over this local cache (fast,
offline, reproducible). Cache file is git-ignored.
"""
import json
import sqlite3
import sys
import time
from datetime import date

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.atlas_data import AtlasOHLCVAdapter  # noqa: E402

ROOT = "/home/user/champion-trader"
CACHE = f"{ROOT}/champion_cache.sqlite"

env = {}
for line in open(f"{ROOT}/.env"):
    s = line.strip()
    if "=" in s and not s.startswith("#"):
        k, v = s.split("=", 1)
        env[k] = v

ad = AtlasOHLCVAdapter(env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"])
universe = json.load(open(f"{ROOT}/backend/data/atlas_universe.json"))["symbols"]

con = sqlite3.connect(CACHE)
con.execute(
    "create table if not exists bars(symbol text, date text, open text, high text, "
    "low text, close text, volume integer, delivery_pct real, primary key(symbol,date))"
)
con.execute("create table if not exists done(symbol text primary key, n integer)")
con.commit()
done = {r[0] for r in con.execute("select symbol from done")}

start, end = date(2007, 1, 1), date.today()
total = len(universe)
print(f"cache build: {total} symbols, {len(done)} already done", flush=True)

for i, sym in enumerate(universe):
    if sym in done:
        continue
    try:
        bars = ad.daily_bars(sym, start, end, as_of=end)
        con.executemany(
            "insert or replace into bars values(?,?,?,?,?,?,?,?)",
            [(sym, b.date.isoformat(), str(b.open), str(b.high), str(b.low),
              str(b.close), b.volume, b.delivery_pct) for b in bars],
        )
        con.execute("insert or replace into done values(?,?)", (sym, len(bars)))
        con.commit()
    except Exception as exc:
        print(f"FAIL {sym}: {exc}", flush=True)
    if (i + 1) % 50 == 0:
        print(f"  {i + 1}/{total} ...", flush=True)
    time.sleep(0.05)

n_sym, n_rows = con.execute("select count(*), coalesce(sum(n),0) from done").fetchone()
print(f"CACHE BUILD COMPLETE: {n_sym} symbols, {n_rows} bars -> {CACHE}", flush=True)
con.close()
