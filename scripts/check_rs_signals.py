"""
Quick diagnostic: print today's RS EMA50x200 golden/death cross signals.
Run from the project root: python scripts/check_rs_signals.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.config import settings

FAST_N, SLOW_N = 50, 200
MIN_ADT = 5e7          # ₹5 crore
BUFFER  = 370          # days of history needed

cutoff = (datetime.now() - timedelta(days=BUFFER)).strftime("%Y-%m-%d")

if not os.path.exists(settings.bars_db_path):
    print(f"ERROR: Bar store not found at {settings.bars_db_path}")
    print("Run: python scripts/ingest_kite_daily.py")
    sys.exit(1)

con = sqlite3.connect(settings.bars_db_path)

# NIFTY 50 closes
nifty_rows = con.execute(
    "SELECT date, close FROM index_bars WHERE index_code='NIFTY 50' AND date>=? ORDER BY date",
    (cutoff,),
).fetchall()
if not nifty_rows:
    print("ERROR: No NIFTY 50 data in index_bars. Run ingest first.")
    sys.exit(1)

nifty = pd.Series(
    [float(r[1]) for r in nifty_rows],
    index=pd.to_datetime([r[0] for r in nifty_rows]),
)
print(f"NIFTY 50 : {len(nifty)} bars  |  last date: {nifty.index[-1].date()}")

# Stock universe
symbols = [r[0] for r in con.execute("SELECT symbol FROM done WHERE n>0 ORDER BY symbol")]
print(f"Universe  : {len(symbols)} symbols\n")

golden, death = [], []

for sym in symbols:
    rows = con.execute(
        "SELECT date, close, volume FROM bars WHERE symbol=? AND date>=? ORDER BY date",
        (sym, cutoff),
    ).fetchall()
    if len(rows) < SLOW_N + 10:
        continue

    idx = pd.to_datetime([r[0] for r in rows])
    sc  = pd.Series([float(r[1]) for r in rows], index=idx)
    vol = pd.Series([int(r[2])   for r in rows], index=idx)

    if (sc * vol).iloc[-60:].mean() < MIN_ADT:
        continue

    common = sc.index.intersection(nifty.index)
    if len(common) < SLOW_N + 10:
        continue

    rs   = sc.loc[common] / nifty.loc[common]
    fast = rs.ewm(span=FAST_N, adjust=False).mean()
    slow = rs.ewm(span=SLOW_N, adjust=False).mean()

    fp, fc = float(fast.iloc[-2]), float(fast.iloc[-1])
    sp, sc2 = float(slow.iloc[-2]), float(slow.iloc[-1])

    if fp <= sp and fc > sc2:
        golden.append((sym, float(sc.iloc[-1])))
    elif fp >= sp and fc < sc2:
        death.append((sym, float(sc.iloc[-1])))

con.close()

print(f"Golden crosses (new BUY signals) : {len(golden)}")
for sym, px in sorted(golden):
    print(f"  {sym:<20} ₹{px:,.2f}")

print(f"\nDeath crosses (new EXIT signals)  : {len(death)}")
for sym, px in sorted(death):
    print(f"  {sym:<20} ₹{px:,.2f}")
