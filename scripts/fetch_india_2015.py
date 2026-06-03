"""Fetch NSE + ^NSEI OHLCV (2013-2021) for the 2015-2020 out-of-sample run -> /tmp/rs_cache_2015.pkl"""
import pickle, warnings
warnings.filterwarnings("ignore")
import pandas as pd, yfinance as yf
from datetime import date, timedelta
from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix

SIM_START=date(2015,1,1); SIM_END=date(2020,12,31)
BUFFER=500; BATCH=50
fetch_start=(SIM_START-timedelta(days=BUFFER)).strftime("%Y-%m-%d")  # ~2013-08 for EMA200 warmup
fetch_end=(SIM_END+timedelta(days=5)).strftime("%Y-%m-%d")
print(f"Fetching NSE + ^NSEI, {fetch_start}..{fetch_end}")

braw=yf.download("^NSEI", start=fetch_start, end=fetch_end, auto_adjust=True, progress=False, timeout=60)
braw.index=pd.to_datetime(braw.index).normalize()
if isinstance(braw.columns, pd.MultiIndex): braw.columns=[c[0] for c in braw.columns]
bench=braw[["Open","High","Low","Close","Volume"]].dropna(subset=["Close"])
print(f"  ^NSEI: {len(bench)} rows ({bench.index.min().date()} -> {bench.index.max().date()})")

syms=get_yfinance_symbols()
stock_data={}; batches=[syms[i:i+BATCH] for i in range(0,len(syms),BATCH)]
for bi,batch in enumerate(batches):
    print(f"  Batch {bi+1}/{len(batches)} ({len(batch)})...", flush=True)
    try:
        raw=yf.download(tickers=batch, start=fetch_start, end=fetch_end, group_by="ticker",
                        auto_adjust=True, threads=True, progress=False, timeout=120)
        if raw.empty: continue
        for sym in batch:
            clean=strip_ns_suffix(sym)
            try:
                if len(batch)>1 and isinstance(raw.columns, pd.MultiIndex):
                    df=raw[sym]
                else:
                    df=raw.copy()
                    if isinstance(df.columns, pd.MultiIndex): df.columns=[c[0] for c in df.columns]
                df=df.dropna(subset=["Close"]); df.index=pd.to_datetime(df.index).normalize()
                if len(df)>=210: stock_data[clean]=df[["Open","High","Low","Close","Volume"]]
            except (KeyError, TypeError): pass
    except Exception as e: print(f"  batch {bi+1} err: {e}")

pickle.dump({"nifty":bench,"stocks":stock_data}, open("/tmp/rs_cache_2015.pkl","wb"))
print(f"Cached {len(stock_data)} stocks + ^NSEI -> /tmp/rs_cache_2015.pkl")
