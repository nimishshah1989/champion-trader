"""
RS Crossover Entry Signal Study
Goal: Find the most robust entry indicator for the rally-building phase
      that maximizes R-multiple (avg_win / abs(avg_loss))

Tests 10 entry signal variants across SMA/EMA period combinations.
Exit: RS reversal (same type as entry — symmetric, patient)
Position cap: 10 and 15
Universe: 5Cr ADT, Jan 2021 – May 2026
"""
import sys, json, pickle, warnings
sys.path.insert(0, '/home/user/champion-trader')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import date

SIM_START  = date(2021, 1, 1)
SIM_END    = date(2026, 5, 31)
CAPITAL    = 1_000_000.0
SL_PCT     = 10.0
RPT        = 0.5
MIN_ADT_CR = 5.0
ADT_CR_BYTES = MIN_ADT_CR * 1e7

CACHE_PATH = "/tmp/rs_price_cache.pkl"

from backend.data.nse_stocks import strip_ns_suffix

# ─── Load cache ───────────────────────────────────────────────────────────────
print("Loading price data from cache...")
with open(CACHE_PATH, "rb") as f:
    cache = pickle.load(f)
nifty_df   = cache["nifty"]
stock_data = cache["stocks"]
print(f"  {len(stock_data)} stocks + Nifty")

nifty_close = nifty_df["Close"]
if isinstance(nifty_close, pd.DataFrame):
    nifty_close = nifty_close.iloc[:, 0]

sim_start_dt = pd.Timestamp(SIM_START)
sim_end_dt   = pd.Timestamp(SIM_END)
nifty_sim    = nifty_close[(nifty_close.index >= sim_start_dt) & (nifty_close.index <= sim_end_dt)]
trading_days_all = [d.strftime("%Y-%m-%d") for d in nifty_sim.index]

print(f"  Simulation: {trading_days_all[0]} → {trading_days_all[-1]} ({len(trading_days_all)} days)")

# ─── Signal variants to test ──────────────────────────────────────────────────
# Each variant is (label, fast_type, fast_n, slow_type, slow_n)
# type: "sma" or "ema"
# Signal: RS fast_ma crosses above/below RS slow_ma
VARIANTS = [
    # Current baseline
    ("RS SMA20×200 (baseline)", "sma", 20,  "sma", 200),
    # EMA equivalents (faster signals)
    ("RS EMA20×200           ", "ema", 20,  "ema", 200),
    ("RS EMA13×200           ", "ema", 13,  "ema", 200),
    # Medium-term crossovers
    ("RS SMA50×200           ", "sma", 50,  "sma", 200),
    ("RS EMA50×200           ", "ema", 50,  "ema", 200),
    # Short long-term (100 as slow)
    ("RS SMA20×100           ", "sma", 20,  "sma", 100),
    ("RS EMA20×100           ", "ema", 20,  "ema", 100),
    # Very fast (momentum-style)
    ("RS EMA10×50            ", "ema", 10,  "ema",  50),
    ("RS SMA10×50            ", "sma", 10,  "sma",  50),
    # Classic price: price SMA50×200 golden cross
    ("Price SMA50×200        ", "sma", 50,  "sma", 200),  # uses price, not RS
]

# ─── Pre-compute signals for each variant ─────────────────────────────────────
def ma(series, ma_type, n):
    if ma_type == "sma":
        return series.rolling(n).mean()
    else:  # ema
        return series.ewm(span=n, adjust=False).mean()

def compute_signals_for_variant(fast_type, fast_n, slow_type, slow_n, use_price=False):
    """Returns dict: sym -> dict: date_str -> (O, H, L, C, fast_prev, slow_prev, fast_cur, slow_cur)"""
    warmup = max(slow_n + 10, 210)
    result = {}
    for sym, df in stock_data.items():
        try:
            common = df.index.intersection(nifty_close.index)
            if len(common) < warmup:
                continue
            sc  = df.loc[common, "Close"].astype(float)
            so  = df.loc[common, "Open"].astype(float)
            sh  = df.loc[common, "High"].astype(float)
            sl_ = df.loc[common, "Low"].astype(float)
            vol = df.loc[common, "Volume"].astype(float)
            nc  = nifty_close.loc[common].astype(float)

            # Stock-level mean ADT filter
            sim_mask = (common >= sim_start_dt) & (common <= sim_end_dt)
            adt_sim = (sc.loc[sim_mask] * vol.loc[sim_mask]).mean()
            if np.isnan(adt_sim) or adt_sim < ADT_CR_BYTES:
                continue

            if use_price:
                series = sc
            else:
                series = sc / nc  # RS ratio

            fast_ma = ma(series, fast_type, fast_n)
            slow_ma = ma(series, slow_type, slow_n)

            sig = {}
            for i in range(warmup, len(common)):
                f_cur  = fast_ma.iloc[i]
                s_cur  = slow_ma.iloc[i]
                f_prev = fast_ma.iloc[i-1]
                s_prev = slow_ma.iloc[i-1]
                if any(np.isnan(v) for v in [f_cur, s_cur, f_prev, s_prev]):
                    continue
                dt_str = common[i].strftime("%Y-%m-%d")
                if dt_str < str(SIM_START) or dt_str > str(SIM_END):
                    continue
                sig[dt_str] = (
                    float(so.iloc[i]),   # 0: O
                    float(sh.iloc[i]),   # 1: H
                    float(sl_.iloc[i]),  # 2: L
                    float(sc.iloc[i]),   # 3: C
                    float(f_prev),       # 4: fast_prev
                    float(s_prev),       # 5: slow_prev
                    float(f_cur),        # 6: fast_cur
                    float(s_cur),        # 7: slow_cur
                )
            if sig:
                result[sym] = sig
        except Exception:
            pass
    return result

O_,H_,L_,C_,FP,SP,FC,SC_ = range(8)

def is_buy(v):
    return v[FP] <= v[SP] and v[FC] > v[SC_]  # crossover up

def is_sell(v):
    return v[FP] >= v[SP] and v[FC] < v[SC_]  # crossover down

def run_sim(sigs, max_pos):
    cash         = CAPITAL
    pos_value    = CAPITAL * (RPT/100) / (SL_PCT/100)
    positions    = {}
    pending_buys = {}
    pending_sells= set()
    equity_hi    = CAPITAL
    max_dd       = 0.0
    trades       = []

    for day in trading_days_all:
        # Execute pending sells
        sells_done = set()
        for sym in list(pending_sells):
            if sym not in positions: sells_done.add(sym); continue
            v = sigs.get(sym, {}).get(day)
            if v is None: sells_done.add(sym); continue
            exit_px = v[O_]
            pos = positions.pop(sym)
            pnl = (exit_px - pos["entry"]) * pos["qty"]
            cash += pos["qty"] * exit_px
            trades.append({"win": pnl>0, "pnl_pct": (exit_px/pos["entry"]-1)*100,
                           "days": (pd.Timestamp(day)-pd.Timestamp(pos["date"])).days})
            sells_done.add(sym)
        pending_sells -= sells_done

        # Execute pending buys
        buys_done = set()
        for sym in list(pending_buys.keys()):
            if len(positions) >= max_pos: break
            if sym in positions: buys_done.add(sym); continue
            v = sigs.get(sym, {}).get(day)
            if v is None or v[O_] <= 0: buys_done.add(sym); continue
            entry_px = v[O_]
            qty = max(1, int(pos_value / entry_px))
            cost = qty * entry_px
            if cost > cash: buys_done.add(sym); continue
            cash -= cost
            sl_px = entry_px * (1 - SL_PCT/100)
            positions[sym] = {"entry": entry_px, "sl": sl_px, "qty": qty, "date": day}
            buys_done.add(sym)
        for sym in buys_done:
            pending_buys.pop(sym, None)

        # SL check + sell signals
        for sym in list(positions.keys()):
            v = sigs.get(sym, {}).get(day)
            if v is None: continue
            pos = positions[sym]
            if v[L_] <= pos["sl"]:
                exit_px = pos["sl"] if v[O_] > pos["sl"] else v[O_]
                pnl = (exit_px - pos["entry"]) * pos["qty"]
                cash += pos["qty"] * exit_px
                positions.pop(sym)
                trades.append({"win": False, "pnl_pct": (exit_px/pos["entry"]-1)*100,
                               "days": (pd.Timestamp(day)-pd.Timestamp(pos["date"])).days})
                continue
            if is_sell(v):
                pending_sells.add(sym)

        # Buy signals
        available = max_pos - len(positions) - len(pending_buys)
        if available > 0:
            added = 0
            for sym, sym_sigs in sigs.items():
                if added >= available: break
                if sym in positions or sym in pending_buys: continue
                v = sym_sigs.get(day)
                if v and is_buy(v):
                    pending_buys[sym] = day
                    added += 1

        # Drawdown
        port_val = cash + sum(
            positions[sym]["qty"] * (
                sigs[sym][day][C_] if day in sigs.get(sym, {}) else positions[sym]["entry"]
            ) for sym in positions
        )
        if port_val > equity_hi: equity_hi = port_val
        dd = (equity_hi - port_val) / equity_hi * 100
        if dd > max_dd: max_dd = dd

    # Close open positions
    last_day = trading_days_all[-1]
    for sym, pos in list(positions.items()):
        v = sigs.get(sym, {}).get(last_day)
        exit_px = v[C_] if v else pos["entry"]
        pnl = (exit_px - pos["entry"]) * pos["qty"]
        cash += pos["qty"] * exit_px
        trades.append({"win": pnl>0, "pnl_pct": (exit_px/pos["entry"]-1)*100,
                       "days": (pd.Timestamp(last_day)-pd.Timestamp(pos["date"])).days})

    total_ret = (cash / CAPITAL - 1) * 100
    years_sim = len(trading_days_all) / 252
    arr = ((cash / CAPITAL) ** (1/years_sim) - 1) * 100
    wins = [t for t in trades if t["win"]]
    losses = [t for t in trades if not t["win"]]
    avg_win  = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    win_rate = 100 * len(wins) / len(trades) if trades else 0
    avg_days = np.mean([t["days"] for t in trades]) if trades else 0
    r_mult   = avg_win / abs(avg_loss) if avg_loss != 0 else 0

    return {
        "trades": len(trades), "wins": len(wins), "win_rate": win_rate,
        "avg_win": avg_win, "avg_loss": avg_loss, "r_mult": r_mult,
        "avg_days": avg_days, "total_ret": total_ret, "arr": arr,
        "max_dd": max_dd, "universe": len(sigs)
    }

# ─── Run all variants ─────────────────────────────────────────────────────────
all_results = []

print("\n" + "="*90)
print(f"{'Variant':<30}  {'Uni':>4}  {'Tr':>4}  {'Win%':>5}  {'AvgWin':>7}  {'AvgLoss':>8}  {'R-Mult':>6}  {'ARR':>6}  {'DD':>5}  {'AvgDays':>8}")
print("="*90)

for label, fast_type, fast_n, slow_type, slow_n in VARIANTS:
    use_price = (label.strip().startswith("Price"))
    print(f"  Computing {label.strip()}...", flush=True, end=" ")
    sigs = compute_signals_for_variant(fast_type, fast_n, slow_type, slow_n, use_price=use_price)
    print(f"({len(sigs)} stocks)", flush=True, end=" ")

    for max_pos in [10, 15]:
        r = run_sim(sigs, max_pos)
        all_results.append({
            "label": label.strip(), "fast": f"{fast_type.upper()}{fast_n}",
            "slow": f"{slow_type.upper()}{slow_n}", "use_price": use_price,
            "max_pos": max_pos, **r
        })

    # Print for MAX_POS=10 and 15
    r10 = all_results[-2]
    r15 = all_results[-1]
    print(f"\n  {label}  {r10['universe']:>4}  {r10['trades']:>4}  {r10['win_rate']:>4.1f}%  {r10['avg_win']:>+6.1f}%  {r10['avg_loss']:>+7.1f}%  {r10['r_mult']:>6.2f}  {r10['arr']:>+5.1f}%  {r10['max_dd']:>4.1f}%  {r10['avg_days']:>7.0f}d  [MAX=10]")
    print(f"  {' '*30}  {r15['universe']:>4}  {r15['trades']:>4}  {r15['win_rate']:>4.1f}%  {r15['avg_win']:>+6.1f}%  {r15['avg_loss']:>+7.1f}%  {r15['r_mult']:>6.2f}  {r15['arr']:>+5.1f}%  {r15['max_dd']:>4.1f}%  {r15['avg_days']:>7.0f}d  [MAX=15]")
    print()

print("="*90)
print("\nR-Mult = avg_win / abs(avg_loss) — higher = better R-multiple per trade")

with open("/tmp/rs_crossover_study.json", "w") as f:
    json.dump(all_results, f, indent=2)
print("Saved /tmp/rs_crossover_study.json")
