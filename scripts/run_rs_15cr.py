"""
RS Crossover Backtest — standalone, inline version
Runs 12 combinations for ADT >= 15 crore universe.
Saves /tmp/rs_results_15cr.json

Cache: stores raw OHLCV data in /tmp/rs_price_cache.pkl to avoid re-fetching.
"""
import sys, json, pickle, warnings
sys.path.insert(0, '/home/user/champion-trader')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import date, timedelta

# ─── Config ──────────────────────────────────────────────────────────────────
SIM_START  = date(2021, 1, 1)
SIM_END    = date(2026, 5, 31)
CAPITAL    = 1_000_000.0
SL_PCT     = 10.0
RPT        = 0.5
MAX_POS    = 10
MIN_ADT_CR = 15.0          # ← 15 crore
VOL_MULT   = 1.5
ADT_CR_BYTES = MIN_ADT_CR * 1e7  # 15 crore = 1,50,00,000

NIFTY_TICKER = "^NSEI"
BUFFER_DAYS  = 420         # warmup for SMA200
BATCH_SIZE   = 50
CACHE_PATH   = "/tmp/rs_price_cache.pkl"

from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix

# ─── 1. Fetch / load raw data ─────────────────────────────────────────────────
fetch_start = (SIM_START - timedelta(days=BUFFER_DAYS)).strftime("%Y-%m-%d")
fetch_end   = (SIM_END + timedelta(days=5)).strftime("%Y-%m-%d")

print("Step 1: Load/fetch price data...")
try:
    with open(CACHE_PATH, "rb") as f:
        cache = pickle.load(f)
    nifty_df   = cache["nifty"]
    stock_data = cache["stocks"]
    print(f"  Loaded from cache: {len(stock_data)} stocks + Nifty")
except (FileNotFoundError, KeyError, Exception) as e:
    print(f"  Cache miss ({e}), fetching from yfinance...")

    # Fetch Nifty with Volume
    nifty_raw = yf.download(NIFTY_TICKER, start=fetch_start, end=fetch_end,
                            auto_adjust=True, progress=False, timeout=60)
    nifty_raw.index = pd.to_datetime(nifty_raw.index).normalize()
    # Flatten MultiIndex columns if present
    if isinstance(nifty_raw.columns, pd.MultiIndex):
        nifty_raw.columns = [col[0] for col in nifty_raw.columns]
    nifty_df = nifty_raw[["Open","High","Low","Close","Volume"]].dropna(subset=["Close"])
    print(f"  Nifty: {len(nifty_df)} rows")

    # Fetch stocks in batches
    all_syms   = get_yfinance_symbols()
    stock_data = {}
    batches    = [all_syms[i:i+BATCH_SIZE] for i in range(0, len(all_syms), BATCH_SIZE)]
    for bi, batch in enumerate(batches):
        print(f"  Batch {bi+1}/{len(batches)} ({len(batch)} symbols)...", flush=True)
        try:
            raw = yf.download(tickers=batch, start=fetch_start, end=fetch_end,
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False, timeout=120)
            if raw.empty:
                continue
            for yf_sym in batch:
                clean = strip_ns_suffix(yf_sym)
                try:
                    if len(batch) > 1:
                        if isinstance(raw.columns, pd.MultiIndex):
                            # level=0 is the ticker symbol
                            df = raw[yf_sym]
                        else:
                            df = raw
                    else:
                        df = raw.copy()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = [col[0] for col in df.columns]
                    df = df.dropna(subset=["Close"])
                    df.index = pd.to_datetime(df.index).normalize()
                    if len(df) >= 210:
                        stock_data[clean] = df[["Open","High","Low","Close","Volume"]]
                except (KeyError, TypeError):
                    pass
        except Exception as exc:
            print(f"  Batch {bi+1} error: {exc}")

    with open(CACHE_PATH, "wb") as f:
        pickle.dump({"nifty": nifty_df, "stocks": stock_data}, f)
    print(f"  Cached {len(stock_data)} stocks to {CACHE_PATH}")

# ─── 2. Compute signals per stock ────────────────────────────────────────────
print(f"\nStep 2: Computing signals (ADT >= {MIN_ADT_CR}Cr)...")
nifty_close = nifty_df["Close"]
if isinstance(nifty_close, pd.DataFrame):
    nifty_close = nifty_close.iloc[:, 0]

# Compute Nifty SMA200 for regime filter
nifty_sma200 = nifty_close.rolling(200).mean()
REGIME_DAYS = set()
for dt, nc, nm in zip(nifty_close.index, nifty_close.values, nifty_sma200.values):
    if not np.isnan(nm) and nc > nm:
        REGIME_DAYS.add(dt.strftime("%Y-%m-%d"))

# Nifty return stats
sim_start_dt = pd.Timestamp(SIM_START)
sim_end_dt   = pd.Timestamp(SIM_END)
nifty_sim    = nifty_close[(nifty_close.index >= sim_start_dt) & (nifty_close.index <= sim_end_dt)]
trading_days_all = [d.strftime("%Y-%m-%d") for d in nifty_sim.index]
nifty_start_val  = float(nifty_sim.iloc[0])
nifty_end_val    = float(nifty_sim.iloc[-1])
nifty_total_ret  = (nifty_end_val / nifty_start_val - 1) * 100
years            = len(nifty_sim) / 252
nifty_arr        = ((nifty_end_val / nifty_start_val) ** (1/years) - 1) * 100

# Nifty max drawdown
cum_max = 0.0; max_dd_nifty = 0.0
for v in nifty_sim.values:
    if v > cum_max: cum_max = v
    dd = (cum_max - v) / cum_max * 100
    if dd > max_dd_nifty: max_dd_nifty = dd

print(f"  Nifty: {nifty_total_ret:.1f}% total | {nifty_arr:.1f}% ARR | {max_dd_nifty:.1f}% max DD")
print(f"  Regime days: {len(REGIME_DAYS)} / {len(trading_days_all)} = {100*len(REGIME_DAYS)/len(trading_days_all):.0f}%")

# Signal indices (tuple layout)
O,H,L,C,P20,P200,R20,R200,PP20,PP200,PR20,PR200,VOL,VOLMA20 = range(14)

def compute_stock_signals(sym, df):
    """Returns dict {date_str: signal_tuple} after ADT and data quality filters."""
    try:
        common = df.index.intersection(nifty_close.index)
        if len(common) < 210:
            return None

        sc    = df.loc[common, "Close"].astype(float)
        so    = df.loc[common, "Open"].astype(float)
        sh    = df.loc[common, "High"].astype(float)
        sl_   = df.loc[common, "Low"].astype(float)
        vol   = df.loc[common, "Volume"].astype(float)
        nc    = nifty_close.loc[common].astype(float)

        rs    = sc / nc
        p20   = sc.rolling(20).mean()
        p200  = sc.rolling(200).mean()
        r20   = rs.rolling(20).mean()
        r200  = rs.rolling(200).mean()
        volma = vol.rolling(20).mean()
        adt   = (sc * vol).rolling(20).mean()  # 20-day avg daily turnover

        sig = {}
        for i in range(201, len(common)):
            # Skip NaN
            vals = [p20.iloc[i], p200.iloc[i], r20.iloc[i], r200.iloc[i],
                    p20.iloc[i-1], p200.iloc[i-1], r20.iloc[i-1], r200.iloc[i-1]]
            if any(np.isnan(v) for v in vals):
                continue
            dt_str = common[i].strftime("%Y-%m-%d")
            if dt_str < str(SIM_START) or dt_str > str(SIM_END):
                continue
            # ADT filter
            adt_val = adt.iloc[i]
            if np.isnan(adt_val) or adt_val < ADT_CR_BYTES:
                continue

            sig[dt_str] = (
                float(so.iloc[i]),   # O=0
                float(sh.iloc[i]),   # H=1
                float(sl_.iloc[i]),  # L=2
                float(sc.iloc[i]),   # C=3
                float(p20.iloc[i]),  # P20=4
                float(p200.iloc[i]), # P200=5
                float(r20.iloc[i]),  # R20=6
                float(r200.iloc[i]), # R200=7
                float(p20.iloc[i-1]),  # PP20=8
                float(p200.iloc[i-1]),# PP200=9
                float(r20.iloc[i-1]), # PR20=10
                float(r200.iloc[i-1]),# PR200=11
                float(vol.iloc[i]),   # VOL=12
                float(volma.iloc[i]) if not np.isnan(volma.iloc[i]) else 0.0, # VOLMA20=13
            )
        return sig if sig else None
    except Exception:
        return None

signals = {}
for sym, df in stock_data.items():
    s = compute_stock_signals(sym, df)
    if s:
        signals[sym] = s

print(f"  Signal-ready stocks: {len(signals)}")

# ─── 3. Simulation ────────────────────────────────────────────────────────────
def is_buy(v, scenario, use_regime, use_volume, day):
    rs_up = v[PR20] <= v[PR200] and v[R20] > v[R200]
    if scenario == "RS_ONLY":
        sig = rs_up
    else:
        both_bull = v[P20] > v[P200] and v[R20] > v[R200]
        if not both_bull:
            return False
        sig = (v[PP20] <= v[PP200] or v[PR20] <= v[PR200])
    if not sig:
        return False
    if use_regime and day not in REGIME_DAYS:
        return False
    if use_volume and v[VOLMA20] > 0 and v[VOL] < VOL_MULT * v[VOLMA20]:
        return False
    return True

def is_sell(v, scenario):
    rs_dn = v[PR20] >= v[PR200] and v[R20] < v[R200]
    p_dn  = v[PP20] >= v[PP200] and v[P20] < v[P200]
    if scenario == "RS_ONLY":
        return rs_dn
    if scenario == "DUAL_EITHER":
        return rs_dn or p_dn
    # DUAL_BOTH
    both_bear = v[P20] < v[P200] and v[R20] < v[R200]
    if not both_bear:
        return False
    return v[PP20] >= v[PP200] or v[PR20] >= v[PR200]

def run_sim(scenario, use_regime, use_volume):
    cash         = CAPITAL
    pos_value    = CAPITAL * (RPT/100) / (SL_PCT/100)
    positions    = {}   # sym -> {entry, sl, qty}
    pending_buys = {}   # sym -> signal_date (buy at next open)
    pending_sells = set()  # syms to sell at next open
    equity_hi    = CAPITAL
    max_dd       = 0.0
    trades       = []

    for day in trading_days_all:
        # Execute pending sells at open
        sells_done = set()
        for sym in list(pending_sells):
            if sym not in positions:
                sells_done.add(sym)
                continue
            v = signals.get(sym, {}).get(day)
            if v is None:
                sells_done.add(sym)
                continue
            exit_px = v[O]
            pos = positions.pop(sym)
            pnl = (exit_px - pos["entry"]) * pos["qty"]
            cash += pos["qty"] * exit_px
            trades.append({
                "win": pnl > 0, "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
                "days": (pd.Timestamp(day) - pd.Timestamp(pos["entry_date"])).days,
                "sl": False
            })
            sells_done.add(sym)
        pending_sells -= sells_done

        # Execute pending buys at open
        buys_done = set()
        for sym, sig_day in list(pending_buys.items()):
            if len(positions) >= MAX_POS:
                break
            if sym in positions:
                buys_done.add(sym)
                continue
            v = signals.get(sym, {}).get(day)
            if v is None:
                buys_done.add(sym)
                continue
            entry_px = v[O]
            if entry_px <= 0:
                buys_done.add(sym)
                continue
            sl_px = entry_px * (1 - SL_PCT/100)
            qty   = max(1, int(pos_value / entry_px))
            cost  = qty * entry_px
            if cost > cash:
                buys_done.add(sym)
                continue
            cash -= cost
            positions[sym] = {"entry": entry_px, "sl": sl_px, "qty": qty,
                              "entry_date": day}
            buys_done.add(sym)
        for sym in buys_done:
            pending_buys.pop(sym, None)

        # Check SL and generate signals for tomorrow
        for sym in list(positions.keys()):
            v = signals.get(sym, {}).get(day)
            if v is None:
                continue
            pos = positions[sym]
            # SL check
            if v[L] <= pos["sl"]:
                exit_px = max(v[O], pos["sl"]) if v[O] <= pos["sl"] else pos["sl"]
                pnl = (exit_px - pos["entry"]) * pos["qty"]
                cash += pos["qty"] * exit_px
                positions.pop(sym)
                trades.append({
                    "win": False, "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
                    "days": (pd.Timestamp(day) - pd.Timestamp(pos["entry_date"])).days,
                    "sl": True
                })
                continue
            # Sell signal
            if is_sell(v, scenario):
                pending_sells.add(sym)

        # Buy signals for tomorrow
        if len(positions) + len(pending_buys) < MAX_POS:
            for sym, sym_sigs in signals.items():
                if sym in positions or sym in pending_buys:
                    continue
                v = sym_sigs.get(day)
                if v and is_buy(v, scenario, use_regime, use_volume, day):
                    pending_buys[sym] = day

        # Portfolio value and drawdown
        port_val = cash + sum(
            positions[sym]["qty"] * (
                signals[sym][day][C] if day in signals.get(sym, {}) else positions[sym]["entry"]
            )
            for sym in positions
        )
        if port_val > equity_hi:
            equity_hi = port_val
        dd = (equity_hi - port_val) / equity_hi * 100
        if dd > max_dd:
            max_dd = dd

    # Close remaining positions at last day close
    last_day = trading_days_all[-1]
    for sym, pos in list(positions.items()):
        v = signals.get(sym, {}).get(last_day)
        exit_px = v[C] if v else pos["entry"]
        pnl = (exit_px - pos["entry"]) * pos["qty"]
        cash += pos["qty"] * exit_px
        trades.append({
            "win": pnl > 0, "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
            "days": (pd.Timestamp(last_day) - pd.Timestamp(pos["entry_date"])).days,
            "sl": False
        })

    # Stats
    total_ret = (cash / CAPITAL - 1) * 100
    years_sim = len(trading_days_all) / 252
    arr       = ((cash / CAPITAL) ** (1/years_sim) - 1) * 100
    wins      = [t for t in trades if t["win"]]
    losses    = [t for t in trades if not t["win"]]
    sl_hits   = [t for t in trades if t["sl"]]
    avg_win   = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss  = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    avg_days  = np.mean([t["days"] for t in trades]) if trades else 0
    win_rate  = 100 * len(wins) / len(trades) if trades else 0
    sl_rate   = 100 * len(sl_hits) / len(trades) if trades else 0

    return {
        "scenario":  scenario,
        "regime":    use_regime,
        "volume":    use_volume,
        "trades":    len(trades),
        "wins":      len(wins),
        "losses":    len(losses),
        "win_rate":  win_rate,
        "avg_win":   avg_win,
        "avg_loss":  avg_loss,
        "sl_rate":   sl_rate,
        "avg_days":  avg_days,
        "total_ret": total_ret,
        "arr":       arr,
        "max_dd":    max_dd,
        "final":     cash,
    }

# ─── 4. Run all 12 combinations ──────────────────────────────────────────────
print("\nStep 3: Running 12 combinations...")
results = []
scenarios = ["RS_ONLY", "DUAL_EITHER", "DUAL_BOTH"]
filters   = [(False, False), (True, False), (False, True), (True, True)]
labels    = {"RS_ONLY":"RS_ONLY", "DUAL_EITHER":"DUAL_EITHER", "DUAL_BOTH":"DUAL_BOTH"}
flabels   = {(False,False):"--", (True,False):"R-", (False,True):"-V", (True,True):"RV"}

for sc in scenarios:
    for (reg, vol) in filters:
        print(f"  {sc} [{flabels[(reg,vol)]}]...", end=" ", flush=True)
        r = run_sim(sc, reg, vol)
        results.append(r)
        print(f"trades={r['trades']}  ARR={r['arr']:+.1f}%  DD={r['max_dd']:.1f}%")

# ─── 5. Save results ─────────────────────────────────────────────────────────
out = {
    "results":           results,
    "nifty_ret":         nifty_total_ret,
    "nifty_arr":         nifty_arr,
    "nifty_max_dd":      max_dd_nifty,
    "sim_start":         str(SIM_START),
    "sim_end":           str(SIM_END),
    "capital":           CAPITAL,
    "sl_pct":            SL_PCT,
    "rpt":               RPT,
    "max_pos":           MAX_POS,
    "universe_size":     len(signals),
    "min_adt_cr":        MIN_ADT_CR,
    "regime_days_in_sim": len(REGIME_DAYS),
    "trading_days_in_sim": len(trading_days_all),
}
with open("/tmp/rs_results_15cr.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"\nSaved /tmp/rs_results_15cr.json")
print(f"Universe: {len(signals)} stocks (ADT >= {MIN_ADT_CR}Cr)")
print(f"Nifty: {nifty_total_ret:.1f}% total | {nifty_arr:.1f}% ARR | {max_dd_nifty:.1f}% max DD")
