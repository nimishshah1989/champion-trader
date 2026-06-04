"""
Quick diagnostic: print today's RS EMA50x200 golden/death cross signals.
Fetches directly from Kite — no bar store needed.

Run from the project root:
    python3 scripts/check_rs_signals.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date, timedelta
import numpy as np
import pandas as pd

from backend.config import settings
from backend.data.nse_stocks import NSE_UNIVERSE
from backend.engine.kite_data import KiteHistoricalAdapter

FAST_N, SLOW_N = 50, 200
MIN_ADT  = 5e7      # ₹5 crore avg daily turnover
BUFFER   = 370      # calendar days of history

if not (settings.kite_api_key and settings.kite_access_token):
    print("ERROR: KITE_API_KEY / KITE_ACCESS_TOKEN not set in .env")
    sys.exit(1)

adapter  = KiteHistoricalAdapter(settings.kite_api_key, settings.kite_access_token)
end_dt   = date.today()
start_dt = end_dt - timedelta(days=BUFFER)

print(f"Fetching NIFTY 50  {start_dt} → {end_dt} ...")
nifty_bars  = adapter.daily_bars("NIFTY 50", start_dt, end_dt)
nifty_close = pd.Series(
    [float(b.close) for b in nifty_bars],
    index=pd.to_datetime([b.date for b in nifty_bars]),
)
print(f"NIFTY 50 : {len(nifty_close)} bars  |  last: {nifty_close.index[-1].date()}")
time.sleep(0.35)

print(f"Fetching {len(NSE_UNIVERSE)} stocks from Kite (this takes ~5 min) ...")

golden, death = [], []
skipped = 0

for i, sym in enumerate(NSE_UNIVERSE, 1):
    try:
        bars = adapter.daily_bars(sym, start_dt, end_dt)
        if len(bars) < SLOW_N + 10:
            time.sleep(0.35)
            continue

        idx = pd.to_datetime([b.date for b in bars])
        sc  = pd.Series([float(b.close)  for b in bars], index=idx)
        vol = pd.Series([b.volume        for b in bars], index=idx)

        if (sc * vol).iloc[-60:].mean() < MIN_ADT:
            time.sleep(0.35)
            continue

        common = sc.index.intersection(nifty_close.index)
        if len(common) < SLOW_N + 10:
            time.sleep(0.35)
            continue

        rs   = sc.loc[common] / nifty_close.loc[common]
        fast = rs.ewm(span=FAST_N, adjust=False).mean()
        slow = rs.ewm(span=SLOW_N, adjust=False).mean()

        fp, fc = float(fast.iloc[-2]), float(fast.iloc[-1])
        sp, sc2 = float(slow.iloc[-2]), float(slow.iloc[-1])

        if fp <= sp and fc > sc2:
            golden.append((sym, float(sc.iloc[-1])))
        elif fp >= sp and fc < sc2:
            death.append((sym, float(sc.iloc[-1])))

    except KeyError:
        skipped += 1
    except Exception as e:
        print(f"  WARN {sym}: {e}")
        skipped += 1

    time.sleep(0.35)
    if i % 50 == 0:
        print(f"  ... {i}/{len(NSE_UNIVERSE)} done")

print(f"\n{'='*50}")
print(f"Golden crosses (new BUY signals) : {len(golden)}")
for sym, px in sorted(golden):
    print(f"  {sym:<20} ₹{px:,.2f}")

print(f"\nDeath crosses (new EXIT signals) : {len(death)}")
for sym, px in sorted(death):
    print(f"  {sym:<20} ₹{px:,.2f}")

print(f"\n({skipped} symbols not found in Kite)")
