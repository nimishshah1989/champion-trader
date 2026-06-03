"""Fetch S&P 500 + benchmark OHLCV (2019-2026) -> /tmp/sp500_cache.pkl"""
import json, pickle, warnings
warnings.filterwarnings("ignore")
import pandas as pd, yfinance as yf
from datetime import date, timedelta

SIM_START=date(2021,1,1); SIM_END=date(2026,5,31)
BUFFER=420; BATCH=50
fetch_start=(SIM_START-timedelta(days=BUFFER)).strftime("%Y-%m-%d")
fetch_end=(SIM_END+timedelta(days=5)).strftime("%Y-%m-%d")

syms=json.load(open("/tmp/sp500_tickers.json"))
print(f"Fetching {len(syms)} S&P500 stocks + ^GSPC, {fetch_start}..{fetch_end}")

# Benchmark
braw=yf.download("^GSPC", start=fetch_start, end=fetch_end, auto_adjust=True, progress=False, timeout=60)
braw.index=pd.to_datetime(braw.index).normalize()
if isinstance(braw.columns, pd.MultiIndex): braw.columns=[c[0] for c in braw.columns]
bench=braw[["Open","High","Low","Close","Volume"]].dropna(subset=["Close"])
print(f"  ^GSPC: {len(bench)} rows")

stock_data={}
batches=[syms[i:i+BATCH] for i in range(0,len(syms),BATCH)]
for bi,batch in enumerate(batches):
    print(f"  Batch {bi+1}/{len(batches)} ({len(batch)})...", flush=True)
    try:
        raw=yf.download(tickers=batch, start=fetch_start, end=fetch_end, group_by="ticker",
                        auto_adjust=True, threads=True, progress=False, timeout=120)
        if raw.empty: continue
        for sym in batch:
            try:
                if len(batch)>1 and isinstance(raw.columns, pd.MultiIndex):
                    df=raw[sym]
                else:
                    df=raw.copy()
                    if isinstance(df.columns, pd.MultiIndex): df.columns=[c[0] for c in df.columns]
                df=df.dropna(subset=["Close"])
                df.index=pd.to_datetime(df.index).normalize()
                if len(df)>=210:
                    stock_data[sym]=df[["Open","High","Low","Close","Volume"]]
            except (KeyError, TypeError): pass
    except Exception as e:
        print(f"  batch {bi+1} err: {e}")

with open("/tmp/sp500_cache.pkl","wb") as f:
    pickle.dump({"nifty":bench,"stocks":stock_data}, f)  # key 'nifty' reused as benchmark
print(f"Cached {len(stock_data)} stocks + benchmark -> /tmp/sp500_cache.pkl")
