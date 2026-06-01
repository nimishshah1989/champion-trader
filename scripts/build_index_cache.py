"""Pull NIFTY benchmark index closes from Atlas -> local cache (for regime + RS)."""
import json
import sqlite3
import sys
import urllib.parse

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.atlas_data import _default_http_get  # noqa: E402

ROOT = "/home/user/champion-trader"
CACHE = f"{ROOT}/champion_cache.sqlite"

env = {}
for line in open(f"{ROOT}/.env"):
    s = line.strip()
    if "=" in s and not s.startswith("#"):
        k, v = s.split("=", 1)
        env[k] = v
URL, KEY = env["SUPABASE_URL"], env["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

con = sqlite3.connect(CACHE)
con.execute("create table if not exists index_bars(index_code text, date text, close real, primary key(index_code,date))")

for code in ["NIFTY 50", "NIFTY 500"]:
    offset, n = 0, 0
    while True:
        q = urllib.parse.quote(code, safe="")
        url = (f"{URL}/rest/v1/de_index_prices?index_code=eq.{q}"
               f"&select=date,close&order=date.asc&limit=1000&offset={offset}")
        rows = json.loads(_default_http_get(url, H))
        con.executemany(
            "insert or replace into index_bars values(?,?,?)",
            [(code, r["date"][:10], float(r["close"])) for r in rows if r.get("close") is not None],
        )
        n += len(rows)
        if len(rows) < 1000:
            break
        offset += 1000
    con.commit()
    rng = con.execute("select min(date),max(date),count(*) from index_bars where index_code=?", (code,)).fetchone()
    print(f"{code}: rows={n}  range {rng[0]}..{rng[1]}")
con.close()
