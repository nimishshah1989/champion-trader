"""
RS Exit Strategy Combination Test
Tests: RS Reversal OR 20% trailing stop (whichever fires first)
Position caps: 10, 15, 20, unlimited (999)
Scenario: RS_ONLY entry, 5Cr ADT universe
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
MIN_ADT_CR = 5.0
ADT_CR_BYTES = MIN_ADT_CR * 1e7
VOL_MULT   = 1.5
TRAIL_PCT  = 20.0   # trailing stop from peak

NIFTY_TICKER = "^NSEI"
BUFFER_DAYS  = 420
CACHE_PATH   = "/tmp/rs_price_cache.pkl"

from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix

# ─── 1. Load cached data ─────────────────────────────────────────────────────
print("Step 1: Loading price data from cache...")
with open(CACHE_PATH, "rb") as f:
    cache = pickle.load(f)
nifty_df   = cache["nifty"]
stock_data = cache["stocks"]
print(f"  Loaded: {len(stock_data)} stocks + Nifty")

# ─── 2. Compute signals ───────────────────────────────────────────────────────
nifty_close = nifty_df["Close"]
if isinstance(nifty_close, pd.DataFrame):
    nifty_close = nifty_close.iloc[:, 0]

nifty_sma200 = nifty_close.rolling(200).mean()
sim_start_dt = pd.Timestamp(SIM_START)
sim_end_dt   = pd.Timestamp(SIM_END)
nifty_sim    = nifty_close[(nifty_close.index >= sim_start_dt) & (nifty_close.index <= sim_end_dt)]

# Regime days (sim period only)
nifty_sma200_sim = nifty_sma200.reindex(nifty_sim.index)
REGIME_DAYS = set()
for dt, nc, nm in zip(nifty_sim.index, nifty_sim.values, nifty_sma200_sim.values):
    if not np.isnan(nm) and nc > nm:
        REGIME_DAYS.add(dt.strftime("%Y-%m-%d"))

trading_days_all = [d.strftime("%Y-%m-%d") for d in nifty_sim.index]

# Signal tuple indices
O,H,L,C,P20,P200,R20,R200,PP20,PP200,PR20,PR200,VOL,VOLMA20 = range(14)

# ATR14 for trailing stop variant (we don't use ATR here, just price-based 20%)
def compute_stock_signals(sym, df):
    try:
        common = df.index.intersection(nifty_close.index)
        if len(common) < 210:
            return None
        sc  = df.loc[common, "Close"].astype(float)
        so  = df.loc[common, "Open"].astype(float)
        sh  = df.loc[common, "High"].astype(float)
        sl_ = df.loc[common, "Low"].astype(float)
        vol = df.loc[common, "Volume"].astype(float)
        nc  = nifty_close.loc[common].astype(float)

        rs     = sc / nc
        p20    = sc.rolling(20).mean()
        p200   = sc.rolling(200).mean()
        r20    = rs.rolling(20).mean()
        r200   = rs.rolling(200).mean()
        volma  = vol.rolling(20).mean()

        # Stock-level mean ADT over sim period
        sim_mask = (common >= sim_start_dt) & (common <= sim_end_dt)
        adt_sim = (sc.loc[sim_mask] * vol.loc[sim_mask]).mean()
        if np.isnan(adt_sim) or adt_sim < ADT_CR_BYTES:
            return None

        sig = {}
        for i in range(201, len(common)):
            vals = [p20.iloc[i], p200.iloc[i], r20.iloc[i], r200.iloc[i],
                    p20.iloc[i-1], p200.iloc[i-1], r20.iloc[i-1], r200.iloc[i-1]]
            if any(np.isnan(v) for v in vals):
                continue
            dt_str = common[i].strftime("%Y-%m-%d")
            if dt_str < str(SIM_START) or dt_str > str(SIM_END):
                continue
            sig[dt_str] = (
                float(so.iloc[i]),    # O
                float(sh.iloc[i]),    # H
                float(sl_.iloc[i]),   # L
                float(sc.iloc[i]),    # C
                float(p20.iloc[i]),   # P20
                float(p200.iloc[i]),  # P200
                float(r20.iloc[i]),   # R20
                float(r200.iloc[i]),  # R200
                float(p20.iloc[i-1]),   # PP20
                float(p200.iloc[i-1]),  # PP200
                float(r20.iloc[i-1]),   # PR20
                float(r200.iloc[i-1]),  # PR200
                float(vol.iloc[i]),   # VOL
                float(volma.iloc[i]) if not np.isnan(volma.iloc[i]) else 0.0,  # VOLMA20
            )
        return sig if sig else None
    except Exception:
        return None

print(f"\nStep 2: Computing signals (stock-level ADT >= {MIN_ADT_CR}Cr over sim period)...")
signals = {}
for sym, df in stock_data.items():
    s = compute_stock_signals(sym, df)
    if s:
        signals[sym] = s
print(f"  Signal-ready stocks: {len(signals)}")

# ─── 3. Simulation ────────────────────────────────────────────────────────────
def is_buy(v, day):
    """RS_ONLY entry: RS SMA20 crosses above SMA200."""
    return v[PR20] <= v[PR200] and v[R20] > v[R200]

def is_sell_rs_reversal(v):
    """Original: RS SMA20 crosses below SMA200."""
    return v[PR20] >= v[PR200] and v[R20] < v[R200]

def run_sim(max_pos, exit_mode):
    """
    exit_mode:
      "rs_reversal" — original RS crossover reversal
      "trail20"     — 20% trailing stop from peak
      "combo"       — RS reversal OR 20% trailing, whichever fires first
    """
    cash         = CAPITAL
    pos_value    = CAPITAL * (RPT/100) / (SL_PCT/100)
    positions    = {}   # sym -> {entry, sl, qty, entry_date, peak}
    pending_buys = {}   # sym -> signal_date
    pending_sells = set()
    equity_hi    = CAPITAL
    max_dd       = 0.0
    trades       = []

    for day in trading_days_all:
        # Execute pending sells at open
        sells_done = set()
        for sym in list(pending_sells):
            if sym not in positions:
                sells_done.add(sym); continue
            v = signals.get(sym, {}).get(day)
            if v is None:
                sells_done.add(sym); continue
            exit_px = v[O]
            pos = positions.pop(sym)
            pnl = (exit_px - pos["entry"]) * pos["qty"]
            cash += pos["qty"] * exit_px
            trades.append({
                "win": pnl > 0, "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
                "days": (pd.Timestamp(day) - pd.Timestamp(pos["entry_date"])).days,
                "sl": False, "exit": "signal"
            })
            sells_done.add(sym)
        pending_sells -= sells_done

        # Execute pending buys at open
        buys_done = set()
        for sym, sig_day in list(pending_buys.items()):
            if len(positions) >= max_pos:
                break
            if sym in positions:
                buys_done.add(sym); continue
            v = signals.get(sym, {}).get(day)
            if v is None or v[O] <= 0:
                buys_done.add(sym); continue
            entry_px = v[O]
            sl_px = entry_px * (1 - SL_PCT/100)
            qty   = max(1, int(pos_value / entry_px))
            cost  = qty * entry_px
            if cost > cash:
                buys_done.add(sym); continue
            cash -= cost
            positions[sym] = {
                "entry": entry_px, "sl": sl_px, "qty": qty,
                "entry_date": day, "peak": entry_px
            }
            buys_done.add(sym)
        for sym in buys_done:
            pending_buys.pop(sym, None)

        # Check SL, update peak, generate sell signals
        for sym in list(positions.keys()):
            v = signals.get(sym, {}).get(day)
            if v is None:
                continue
            pos = positions[sym]

            # Update peak price for trailing stop
            if v[H] > pos["peak"]:
                pos["peak"] = v[H]

            # Hard SL check (10%)
            if v[L] <= pos["sl"]:
                exit_px = pos["sl"] if v[O] > pos["sl"] else v[O]
                pnl = (exit_px - pos["entry"]) * pos["qty"]
                cash += pos["qty"] * exit_px
                positions.pop(sym)
                trades.append({
                    "win": False, "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
                    "days": (pd.Timestamp(day) - pd.Timestamp(pos["entry_date"])).days,
                    "sl": True, "exit": "stop"
                })
                continue

            # Trailing stop check (20% from peak)
            trail_trigger = False
            if exit_mode in ("trail20", "combo"):
                trail_floor = pos["peak"] * (1 - TRAIL_PCT/100)
                if v[L] <= trail_floor:
                    trail_trigger = True
                    exit_px = trail_floor if v[O] > trail_floor else v[O]
                    pnl = (exit_px - pos["entry"]) * pos["qty"]
                    cash += pos["qty"] * exit_px
                    positions.pop(sym)
                    trades.append({
                        "win": pnl > 0, "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
                        "days": (pd.Timestamp(day) - pd.Timestamp(pos["entry_date"])).days,
                        "sl": False, "exit": "trail"
                    })

            if trail_trigger:
                continue

            # RS reversal sell signal
            sell_sig = False
            if exit_mode == "rs_reversal":
                sell_sig = is_sell_rs_reversal(v)
            elif exit_mode == "combo":
                sell_sig = is_sell_rs_reversal(v)
            # trail20 doesn't use RS reversal

            if sell_sig:
                pending_sells.add(sym)

        # Buy signals for tomorrow
        available_slots = max_pos - len(positions) - len(pending_buys)
        if available_slots > 0:
            added = 0
            for sym, sym_sigs in signals.items():
                if added >= available_slots:
                    break
                if sym in positions or sym in pending_buys:
                    continue
                v = sym_sigs.get(day)
                if v and is_buy(v, day):
                    pending_buys[sym] = day
                    added += 1

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
            "sl": False, "exit": "eod"
        })

    total_ret = (cash / CAPITAL - 1) * 100
    years_sim = len(trading_days_all) / 252
    arr       = ((cash / CAPITAL) ** (1/years_sim) - 1) * 100
    wins      = [t for t in trades if t["win"]]
    losses    = [t for t in trades if not t["win"]]
    sl_hits   = [t for t in trades if t["sl"]]
    trail_hits = [t for t in trades if t.get("exit") == "trail"]
    avg_win   = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss  = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    avg_days  = np.mean([t["days"] for t in trades]) if trades else 0
    win_rate  = 100 * len(wins) / len(trades) if trades else 0

    return {
        "exit_mode":   exit_mode,
        "max_pos":     max_pos,
        "trades":      len(trades),
        "wins":        len(wins),
        "losses":      len(losses),
        "win_rate":    win_rate,
        "avg_win":     avg_win,
        "avg_loss":    avg_loss,
        "sl_hits":     len(sl_hits),
        "trail_hits":  len(trail_hits),
        "avg_days":    avg_days,
        "total_ret":   total_ret,
        "arr":         arr,
        "max_dd":      max_dd,
        "final":       cash,
    }

# ─── 4. Run tests ─────────────────────────────────────────────────────────────
print("\nStep 3: Running exit strategy + position cap tests...")
print("─" * 75)

results = []

# A: Exit strategy comparison (MAX_POS=10, RS_ONLY entry)
exit_modes = [
    ("rs_reversal", "RS Reversal only        "),
    ("trail20",     "20% Trailing only       "),
    ("combo",       "RS Reversal OR 20% Trail"),
]
print("\n[A] Exit strategy comparison (MAX_POS=10):")
print(f"  {'Exit Mode':<28}  {'Trades':>6}  {'Win%':>5}  {'AvgWin':>7}  {'AvgLoss':>8}  {'ARR':>6}  {'DD':>5}  {'Trail%':>7}")
for mode, label in exit_modes:
    r = run_sim(max_pos=10, exit_mode=mode)
    results.append(r)
    trail_pct = 100*r["trail_hits"]/r["trades"] if r["trades"] else 0
    print(f"  {label}  {r['trades']:>6}  {r['win_rate']:>4.1f}%  {r['avg_win']:>+6.1f}%  {r['avg_loss']:>+7.1f}%  {r['arr']:>+5.1f}%  {r['max_dd']:>4.1f}%  {trail_pct:>5.1f}%")

# B: Position cap comparison (combo exit)
caps = [10, 15, 20, 999]
cap_labels = {10: "MAX_POS = 10      ", 15: "MAX_POS = 15      ",
              20: "MAX_POS = 20      ", 999: "Unlimited         "}
print("\n[B] Position cap comparison (RS Reversal OR 20% Trail exit):")
print(f"  {'Cap':<20}  {'Trades':>6}  {'Win%':>5}  {'AvgWin':>7}  {'ARR':>6}  {'DD':>5}  {'Trail%':>7}")
for cap in caps:
    r = run_sim(max_pos=cap, exit_mode="combo")
    results.append(r)
    trail_pct = 100*r["trail_hits"]/r["trades"] if r["trades"] else 0
    print(f"  {cap_labels[cap]}  {r['trades']:>6}  {r['win_rate']:>4.1f}%  {r['avg_win']:>+6.1f}%  {r['arr']:>+5.1f}%  {r['max_dd']:>4.1f}%  {trail_pct:>5.1f}%")

# C: Position cap comparison (rs_reversal only — for comparison)
print("\n[C] Position cap comparison (RS Reversal exit only — reference):")
print(f"  {'Cap':<20}  {'Trades':>6}  {'Win%':>5}  {'AvgWin':>7}  {'ARR':>6}  {'DD':>5}")
for cap in caps:
    r = run_sim(max_pos=cap, exit_mode="rs_reversal")
    results.append(r)
    print(f"  {cap_labels[cap]}  {r['trades']:>6}  {r['win_rate']:>4.1f}%  {r['avg_win']:>+6.1f}%  {r['arr']:>+5.1f}%  {r['max_dd']:>4.1f}%")

print("\n─" * 75)
print("Done.")

out = {"results": results, "sim_start": str(SIM_START), "sim_end": str(SIM_END),
       "capital": CAPITAL, "sl_pct": SL_PCT, "trail_pct": TRAIL_PCT,
       "universe_size": len(signals)}
with open("/tmp/rs_exit_combo.json", "w") as f:
    json.dump(out, f, indent=2)
print("Saved /tmp/rs_exit_combo.json")
