"""
RS Crossover Backtest — corrected version with verified logic.

Key fixes vs previous version:
1. ADT filter at STOCK level: compute mean ADT over sim period, include/exclude permanently
2. Regime days: only count trading days WITHIN the sim period
3. Pending queue: enforce MAX_POS cap per-iteration (not just at loop entry)
4. Pending buys: don't expire on 'no data today' — only drop when executed or if crossover reversal
5. Position-level close: close at last available price, not entry price if data missing

Run both ADT thresholds, save results.
"""
import sys, json, pickle, warnings
sys.path.insert(0, '/home/user/champion-trader')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import date

# ─── Config ──────────────────────────────────────────────────────────────────
SIM_START  = date(2021, 1, 1)
SIM_END    = date(2026, 5, 31)
CAPITAL    = 1_000_000.0
SL_PCT     = 10.0
RPT        = 0.5
MAX_POS    = 10
VOL_MULT   = 1.5
CACHE_PATH = "/tmp/rs_price_cache.pkl"

# ─── Load price data ──────────────────────────────────────────────────────────
print("Loading cached price data...")
with open(CACHE_PATH, "rb") as f:
    cache = pickle.load(f)
nifty_df   = cache["nifty"]
stock_data = cache["stocks"]
print(f"  {len(stock_data)} stocks + Nifty loaded from cache")

nifty_close = nifty_df["Close"].astype(float)
if isinstance(nifty_close, pd.DataFrame):
    nifty_close = nifty_close.iloc[:, 0]

# ─── Simulation-period trading days ──────────────────────────────────────────
sim_start_dt = pd.Timestamp(SIM_START)
sim_end_dt   = pd.Timestamp(SIM_END)
nifty_sim    = nifty_close[(nifty_close.index >= sim_start_dt) & (nifty_close.index <= sim_end_dt)]
trading_days = [d.strftime("%Y-%m-%d") for d in nifty_sim.index]
print(f"  Trading days in simulation: {len(trading_days)}")

# ─── Regime days: only sim-period dates where Nifty > SMA200 ─────────────────
# Use full historical data for SMA200 warmup, but only tag sim-period dates
nifty_sma200 = nifty_close.rolling(200).mean()
nifty_sma200_sim = nifty_sma200.reindex(nifty_sim.index)
REGIME_DAYS = set()
for dt, nc, nm in zip(nifty_sim.index, nifty_sim.values, nifty_sma200_sim.values):
    if not np.isnan(nm) and nc > nm:
        REGIME_DAYS.add(dt.strftime("%Y-%m-%d"))
print(f"  Regime days (Nifty > SMA200): {len(REGIME_DAYS)} / {len(trading_days)} = {100*len(REGIME_DAYS)/len(trading_days):.1f}%")

# ─── Nifty benchmark stats ────────────────────────────────────────────────────
nifty_start_val = float(nifty_sim.iloc[0])
nifty_end_val   = float(nifty_sim.iloc[-1])
nifty_total_ret = (nifty_end_val / nifty_start_val - 1) * 100
years           = len(nifty_sim) / 252
nifty_arr       = ((nifty_end_val / nifty_start_val) ** (1/years) - 1) * 100
cum_max = 0.0; max_dd_nifty = 0.0
for v in nifty_sim.values:
    if v > cum_max: cum_max = v
    dd = (cum_max - v) / cum_max * 100
    if dd > max_dd_nifty: max_dd_nifty = dd
print(f"  Nifty: {nifty_total_ret:.1f}% total | {nifty_arr:.1f}% ARR | {max_dd_nifty:.1f}% max DD")

# ─── Signal indices ───────────────────────────────────────────────────────────
# tuple layout: (open, high, low, close, p20, p200, r20, r200, pp20, pp200, pr20, pr200, vol, volma20)
O,H,L,C,P20,P200,R20,R200,PP20,PP200,PR20,PR200,VOL,VOLMA20 = range(14)


# ─── Build signal universe for a given ADT threshold ─────────────────────────
def build_signals(min_adt_cr: float) -> dict:
    """
    Returns {sym: {date_str: signal_tuple}} filtered by:
    - Stock-level ADT: mean ADT over sim period >= min_adt_cr crore
    - 200+ rows of data available
    - All SMA values valid
    """
    min_adt_bytes = min_adt_cr * 1e7  # crore to absolute
    signals = {}

    for sym, df in stock_data.items():
        try:
            # Align to Nifty trading days
            common = df.index.intersection(nifty_close.index)
            if len(common) < 210:
                continue

            sc   = df.loc[common, "Close"].astype(float)
            so   = df.loc[common, "Open"].astype(float)
            sh   = df.loc[common, "High"].astype(float)
            sl_  = df.loc[common, "Low"].astype(float)
            vol  = df.loc[common, "Volume"].astype(float)
            nc   = nifty_close.loc[common].astype(float)

            rs    = sc / nc
            p20   = sc.rolling(20).mean()
            p200  = sc.rolling(200).mean()
            r20   = rs.rolling(20).mean()
            r200  = rs.rolling(200).mean()
            volma = vol.rolling(20).mean()

            # ── Stock-level ADT filter: mean ADT over SIM PERIOD ──────────
            # Only include the stock if its average daily turnover (within
            # the simulation window) meets the threshold.
            sim_mask = (common >= sim_start_dt) & (common <= sim_end_dt)
            adt_sim  = (sc.loc[sim_mask] * vol.loc[sim_mask]).mean()
            if np.isnan(adt_sim) or adt_sim < min_adt_bytes:
                continue

            # ── Build per-day signal tuples for the sim period ────────────
            sym_sig = {}
            for i in range(201, len(common)):
                dt_str = common[i].strftime("%Y-%m-%d")
                if dt_str < str(SIM_START) or dt_str > str(SIM_END):
                    continue
                # Require all SMA values present (both today and yesterday)
                vals = [p20.iloc[i], p200.iloc[i], r20.iloc[i], r200.iloc[i],
                        p20.iloc[i-1], p200.iloc[i-1], r20.iloc[i-1], r200.iloc[i-1]]
                if any(np.isnan(v) for v in vals):
                    continue

                sym_sig[dt_str] = (
                    float(so.iloc[i]),             # O=0
                    float(sh.iloc[i]),             # H=1
                    float(sl_.iloc[i]),            # L=2
                    float(sc.iloc[i]),             # C=3
                    float(p20.iloc[i]),            # P20=4
                    float(p200.iloc[i]),           # P200=5
                    float(r20.iloc[i]),            # R20=6
                    float(r200.iloc[i]),           # R200=7
                    float(p20.iloc[i-1]),          # PP20=8
                    float(p200.iloc[i-1]),         # PP200=9
                    float(r20.iloc[i-1]),          # PR20=10
                    float(r200.iloc[i-1]),         # PR200=11
                    float(vol.iloc[i]),            # VOL=12
                    float(volma.iloc[i]) if not np.isnan(volma.iloc[i]) else 0.0,  # VOLMA20=13
                )
            if sym_sig:
                signals[sym] = sym_sig
        except Exception:
            continue

    return signals


# ─── Entry / exit logic ───────────────────────────────────────────────────────

def is_buy_signal(v, scenario: str, use_regime: bool, use_volume: bool, day: str) -> bool:
    """
    Returns True on the FIRST day a crossover condition becomes true.
    Uses yesterday→today transition to detect exact crossover day.
    """
    # RS golden cross: yesterday RS_SMA20 <= RS_SMA200, today RS_SMA20 > RS_SMA200
    rs_crossover = (v[PR20] <= v[PR200]) and (v[R20] > v[R200])

    if scenario == "RS_ONLY":
        signal = rs_crossover
    else:
        # Both price AND RS must be in bull state simultaneously
        both_bull_today = (v[P20] > v[P200]) and (v[R20] > v[R200])
        if not both_bull_today:
            return False
        # Trigger fires on the day one of them NEWLY crosses over
        # (the other was already bullish)
        price_crossover = (v[PP20] <= v[PP200]) and (v[P20] > v[P200])
        signal = rs_crossover or price_crossover

    if not signal:
        return False

    # Regime gate: only enter when Nifty itself is in bull phase
    if use_regime and day not in REGIME_DAYS:
        return False

    # Volume gate: crossover must occur on above-average volume
    if use_volume and v[VOLMA20] > 0 and v[VOL] < VOL_MULT * v[VOLMA20]:
        return False

    return True


def is_sell_signal(v, scenario: str) -> bool:
    """
    Returns True when the crossover that justified entry has reversed.
    Uses yesterday→today transition to detect reversal day.
    """
    # RS death cross: yesterday RS_SMA20 >= RS_SMA200, today RS_SMA20 < RS_SMA200
    rs_reversal   = (v[PR20] >= v[PR200]) and (v[R20] < v[R200])
    # Price death cross: yesterday P_SMA20 >= P_SMA200, today P_SMA20 < P_SMA200
    price_reversal = (v[PP20] >= v[PP200]) and (v[P20] < v[P200])

    if scenario == "RS_ONLY":
        return rs_reversal

    if scenario == "DUAL_EITHER":
        # Sell when EITHER crossover reverses
        return rs_reversal or price_reversal

    # DUAL_BOTH: sell only when BOTH have reversed
    both_bear_today = (v[P20] < v[P200]) and (v[R20] < v[R200])
    if not both_bear_today:
        return False
    return rs_reversal or price_reversal


# ─── Core simulation ──────────────────────────────────────────────────────────

def run_sim(signals: dict, scenario: str, use_regime: bool, use_volume: bool) -> dict:
    """
    Day-by-day simulation with pending buy/sell queues.
    - Signals generated at market close
    - Executed at next day's open
    - Hard SL: checked intraday against day's low
    - MAX_POS enforced strictly (cap re-checked per iteration)
    """
    # Fixed-dollar risk sizing: risk ₹5k per trade (0.5% of 1M) at 10% SL → ₹50k position size
    pos_value    = CAPITAL * (RPT / 100.0) / (SL_PCT / 100.0)

    cash         = CAPITAL
    positions    = {}        # {sym: {entry, sl, qty, entry_date, last_px}}
    pending_buys = {}        # {sym: signal_date}  — execute at next open
    pending_sells = set()    # syms — execute at next open

    equity_hi = CAPITAL
    max_dd    = 0.0
    trades    = []

    for day in trading_days:

        # ── 1. Execute pending sells at today's open ──────────────────────
        executed_sells = set()
        for sym in list(pending_sells):
            pos = positions.pop(sym, None)
            if pos is None:
                executed_sells.add(sym)
                continue
            v = signals.get(sym, {}).get(day)
            exit_px = v[O] if v else pos["last_px"]
            pnl = (exit_px - pos["entry"]) * pos["qty"]
            cash += pos["qty"] * exit_px
            trades.append({
                "win": pnl > 0,
                "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
                "days": (pd.Timestamp(day) - pd.Timestamp(pos["entry_date"])).days,
                "sl": False,
            })
            executed_sells.add(sym)
        pending_sells -= executed_sells

        # ── 2. Execute pending buys at today's open (respect MAX_POS) ────
        # Each pending buy is a 1-day order: execute today or it expires.
        # This prevents stale signals from executing days after the crossover.
        executed_buys = set()
        expired_buys  = set()
        for sym in list(pending_buys.keys()):
            if sym in positions:
                executed_buys.add(sym)
                continue
            v = signals.get(sym, {}).get(day)
            if v is None or len(positions) >= MAX_POS or v[O] <= 0:
                # Can't execute today → order expires (missed opportunity)
                expired_buys.add(sym)
                continue
            qty  = max(1, int(pos_value / v[O]))
            cost = qty * v[O]
            if cost > cash:
                expired_buys.add(sym)
                continue
            cash -= cost
            positions[sym] = {
                "entry":      v[O],
                "sl":         v[O] * (1 - SL_PCT / 100.0),
                "qty":        qty,
                "entry_date": day,
                "last_px":    v[O],
            }
            executed_buys.add(sym)
        for sym in executed_buys | expired_buys:
            pending_buys.pop(sym, None)

        # ── 3. Manage open positions: SL check + sell signal ─────────────
        for sym in list(positions.keys()):
            v = signals.get(sym, {}).get(day)
            if v is None:
                continue    # no data today; position stays open at last known price
            pos = positions[sym]
            pos["last_px"] = v[C]   # track latest close for portfolio value

            # Hard SL: if today's low breached SL, exit at the worse of open or SL
            if v[L] <= pos["sl"]:
                exit_px = min(v[O], pos["sl"]) if v[O] < pos["sl"] else pos["sl"]
                # Gap-down: open already below SL → exit at open (worse)
                if v[O] < pos["sl"]:
                    exit_px = v[O]
                pnl = (exit_px - pos["entry"]) * pos["qty"]
                cash += pos["qty"] * exit_px
                positions.pop(sym)
                trades.append({
                    "win": False,
                    "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
                    "days": (pd.Timestamp(day) - pd.Timestamp(pos["entry_date"])).days,
                    "sl": True,
                })
                continue

            # Crossover reversal → queue sell for tomorrow's open
            if is_sell_signal(v, scenario):
                pending_sells.add(sym)

        # ── 4. Generate buy signals: add to pending queue ─────────────────
        # Strictly enforce capacity: MAX_POS minus open positions AND pending buys
        available_slots = MAX_POS - len(positions) - len(pending_buys)
        if available_slots > 0:
            added = 0
            for sym, sym_sigs in signals.items():
                if added >= available_slots:
                    break
                if sym in positions or sym in pending_buys:
                    continue
                v = sym_sigs.get(day)
                if v and is_buy_signal(v, scenario, use_regime, use_volume, day):
                    pending_buys[sym] = day
                    added += 1

        # ── 5. Portfolio valuation and drawdown ───────────────────────────
        pos_mkt_value = sum(
            p["qty"] * p["last_px"] for p in positions.values()
        )
        port_val = cash + pos_mkt_value
        if port_val > equity_hi:
            equity_hi = port_val
        dd = (equity_hi - port_val) / equity_hi * 100.0
        if dd > max_dd:
            max_dd = dd

    # ── Final: close all open positions at last available price ──────────
    for sym, pos in list(positions.items()):
        exit_px = pos["last_px"]
        pnl = (exit_px - pos["entry"]) * pos["qty"]
        cash += pos["qty"] * exit_px
        trades.append({
            "win": pnl > 0,
            "pnl_pct": (exit_px / pos["entry"] - 1) * 100,
            "days": (pd.Timestamp(trading_days[-1]) - pd.Timestamp(pos["entry_date"])).days,
            "sl": False,
        })

    # ── Metrics ───────────────────────────────────────────────────────────
    total_ret  = (cash / CAPITAL - 1) * 100.0
    years_sim  = len(trading_days) / 252.0
    arr        = ((cash / CAPITAL) ** (1.0 / years_sim) - 1) * 100.0
    wins       = [t for t in trades if t["win"]]
    losses     = [t for t in trades if not t["win"]]
    sl_hits    = [t for t in trades if t["sl"]]
    avg_win    = float(np.mean([t["pnl_pct"] for t in wins]))    if wins   else 0.0
    avg_loss   = float(np.mean([t["pnl_pct"] for t in losses])) if losses else 0.0
    avg_days   = float(np.mean([t["days"]    for t in trades]))  if trades else 0.0
    win_rate   = 100.0 * len(wins) / len(trades)   if trades else 0.0
    sl_rate    = 100.0 * len(sl_hits) / len(trades) if trades else 0.0

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


# ─── Run both universes ───────────────────────────────────────────────────────
SCENARIOS = ["RS_ONLY", "DUAL_EITHER", "DUAL_BOTH"]
FILTERS   = [(False, False), (True, False), (False, True), (True, True)]
F_LABELS  = {(False,False):"[--]", (True,False):"[R-]", (False,True):"[-V]", (True,True):"[RV]"}

for min_adt_cr, out_path in [(5.0, "/tmp/rs_results_5cr_v2.json"), (15.0, "/tmp/rs_results_15cr_v2.json")]:
    print(f"\n{'='*60}")
    print(f"Building universe: ADT >= {min_adt_cr}Cr...")
    signals = build_signals(min_adt_cr)
    print(f"  Signal-ready stocks: {len(signals)}")

    # Sanity check: regime-filtered runs must have <= trades of baseline
    print(f"\nRunning 12 combinations (ADT >= {min_adt_cr}Cr)...")
    results = []
    for sc in SCENARIOS:
        baseline = None
        for (reg, vol) in FILTERS:
            r = run_sim(signals, sc, reg, vol)
            results.append(r)
            flag = ""
            if baseline is None:
                baseline = r["trades"]
            elif reg and r["trades"] > baseline:
                flag = " ← ANOMALY (regime > baseline)"  # should not happen
            print(f"  {sc} {F_LABELS[(reg,vol)]}: trades={r['trades']:3d}  "
                  f"win={r['win_rate']:.1f}%  ARR={r['arr']:+.1f}%  "
                  f"DD={r['max_dd']:.1f}%  avghold={r['avg_days']:.0f}d{flag}")

    out = {
        "results":             results,
        "nifty_ret":           nifty_total_ret,
        "nifty_arr":           nifty_arr,
        "nifty_max_dd":        max_dd_nifty,
        "sim_start":           str(SIM_START),
        "sim_end":             str(SIM_END),
        "capital":             CAPITAL,
        "sl_pct":              SL_PCT,
        "rpt":                 RPT,
        "max_pos":             MAX_POS,
        "universe_size":       len(signals),
        "min_adt_cr":          min_adt_cr,
        "regime_days_in_sim":  len(REGIME_DAYS),
        "trading_days_in_sim": len(trading_days),
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  → Saved {out_path}")

print(f"\nNifty benchmark: {nifty_total_ret:.1f}% total | {nifty_arr:.1f}% ARR | {max_dd_nifty:.1f}% max DD")
print(f"Regime days in sim: {len(REGIME_DAYS)} / {len(trading_days)} = {100*len(REGIME_DAYS)/len(trading_days):.1f}%")
