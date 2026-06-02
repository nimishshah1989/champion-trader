"""
FINAL COMPREHENSIVE SIMULATION + HTML REPORT
─────────────────────────────────────────────
Strategy : RS EMA50 × EMA200 crossover (Relative Strength vs Nifty 50)
Entry    : RS EMA50 crosses ABOVE RS EMA200 (rally-building phase)
Exit     : RS EMA50 crosses BELOW RS EMA200 (symmetric) OR 10% hard stop
Capital  : ₹10,00,000 (10 lakh)
Stop loss: 10% hard from entry
Max pos  : 15 concurrent positions
Sizing   : Fixed-risk ₹ per trade = Capital × RPT(0.5%) / SL(10%) = ₹50,000/trade
Universe : Stocks with mean daily turnover ≥ ₹5 crore over sim period
Period   : 1 Jan 2021 → 31 May 2026
Sizing realism: signal at close, fill at next open, 1-day order expiry.

Outputs full analytics HTML: equity curve, drawdown, benchmark, tax,
trade ledger, risk & return metrics → docs/rs_ema50_final_report.html
"""
import sys, json, pickle, warnings
sys.path.insert(0, '/home/user/champion-trader')
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import date

# ─── Config ──────────────────────────────────────────────────────────────────
SIM_START   = date(2015, 1, 1)
SIM_END     = date(2020, 12, 31)
CAPITAL     = 1_000_000.0      # ₹10 lakh
SL_PCT      = 10.0
RPT         = 0.5
MAX_POS     = 15
MIN_ADT_CR  = 5.0
ADT_CR_BYTES= MIN_ADT_CR * 1e7
FAST_N      = 50               # EMA50 on RS
SLOW_N      = 200              # EMA200 on RS
RISK_FREE   = 6.5              # % annual risk-free (India ~10yr G-Sec) for Sharpe/Sortino

# Indian capital gains tax (post Jul-2024 rates)
STCG_RATE   = 20.0            # holding < 12 months
LTCG_RATE   = 12.5           # holding ≥ 12 months
LTCG_EXEMPT = 125_000.0      # ₹1.25 lakh annual LTCG exemption

CACHE_PATH  = "/tmp/rs_cache_2015.pkl"

# ─── Load cached data ────────────────────────────────────────────────────────
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
trading_days = [d.strftime("%Y-%m-%d") for d in nifty_sim.index]
nifty_curve  = {d.strftime("%Y-%m-%d"): float(v) for d, v in zip(nifty_sim.index, nifty_sim.values)}
print(f"  Sim window: {trading_days[0]} → {trading_days[-1]} ({len(trading_days)} trading days)")

# ─── Compute EMA50×200 RS signals ────────────────────────────────────────────
def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

# tuple layout
O_,H_,L_,C_,FP,SP,FC,SC_ = range(8)

print(f"\nComputing RS EMA{FAST_N}×{SLOW_N} signals (ADT ≥ ₹{MIN_ADT_CR}cr)...")
signals = {}
warmup = max(SLOW_N + 10, 210)
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

        sim_mask = (common >= sim_start_dt) & (common <= sim_end_dt)
        adt_sim = (sc.loc[sim_mask] * vol.loc[sim_mask]).mean()
        if np.isnan(adt_sim) or adt_sim < ADT_CR_BYTES:
            continue

        rs = sc / nc
        fast = ema(rs, FAST_N)
        slow = ema(rs, SLOW_N)

        sig = {}
        for i in range(warmup, len(common)):
            fc, scur, fp, sp = fast.iloc[i], slow.iloc[i], fast.iloc[i-1], slow.iloc[i-1]
            if any(np.isnan(v) for v in [fc, scur, fp, sp]):
                continue
            dt_str = common[i].strftime("%Y-%m-%d")
            if dt_str < str(SIM_START) or dt_str > str(SIM_END):
                continue
            sig[dt_str] = (float(so.iloc[i]), float(sh.iloc[i]), float(sl_.iloc[i]),
                           float(sc.iloc[i]), float(fp), float(sp), float(fc), float(scur))
        if sig:
            signals[sym] = sig
    except Exception:
        pass
print(f"  Universe: {len(signals)} stocks")

def is_buy(v):  return v[FP] <= v[SP] and v[FC] > v[SC_]
def is_sell(v): return v[FP] >= v[SP] and v[FC] < v[SC_]

# ─── Simulation ──────────────────────────────────────────────────────────────
print("\nRunning simulation...")
cash          = CAPITAL
pos_value     = CAPITAL * (RPT/100) / (SL_PCT/100)   # ₹50,000
positions     = {}
pending_buys  = {}
pending_sells = set()
equity_hi     = CAPITAL
max_dd        = 0.0
trades        = []
equity_curve  = []   # list of (date, port_val, cash, invested, n_pos)

for day in trading_days:
    # Pending sells at open
    done = set()
    for sym in list(pending_sells):
        if sym not in positions: done.add(sym); continue
        v = signals.get(sym, {}).get(day)
        if v is None: done.add(sym); continue
        px = v[O_]; pos = positions.pop(sym)
        pnl = (px - pos["entry"]) * pos["qty"]
        cash += pos["qty"] * px
        trades.append({"sym": sym, "entry": pos["entry"], "exit": px, "qty": pos["qty"],
                       "entry_date": pos["date"], "exit_date": day, "pnl": pnl,
                       "pnl_pct": (px/pos["entry"]-1)*100,
                       "days": (pd.Timestamp(day)-pd.Timestamp(pos["date"])).days,
                       "reason": "RS reversal"})
        done.add(sym)
    pending_sells -= done

    # Pending buys at open
    done = set()
    for sym in list(pending_buys.keys()):
        if len(positions) >= MAX_POS: break
        if sym in positions: done.add(sym); continue
        v = signals.get(sym, {}).get(day)
        if v is None or v[O_] <= 0: done.add(sym); continue
        px = v[O_]; qty = max(1, int(pos_value / px)); cost = qty * px
        if cost > cash: done.add(sym); continue
        cash -= cost
        positions[sym] = {"entry": px, "sl": px*(1-SL_PCT/100), "qty": qty, "date": day}
        done.add(sym)
    for sym in done: pending_buys.pop(sym, None)

    # SL check + sell signals
    for sym in list(positions.keys()):
        v = signals.get(sym, {}).get(day)
        if v is None: continue
        pos = positions[sym]
        if v[L_] <= pos["sl"]:
            px = pos["sl"] if v[O_] > pos["sl"] else v[O_]
            pnl = (px - pos["entry"]) * pos["qty"]
            cash += pos["qty"] * px
            positions.pop(sym)
            trades.append({"sym": sym, "entry": pos["entry"], "exit": px, "qty": pos["qty"],
                           "entry_date": pos["date"], "exit_date": day, "pnl": pnl,
                           "pnl_pct": (px/pos["entry"]-1)*100,
                           "days": (pd.Timestamp(day)-pd.Timestamp(pos["date"])).days,
                           "reason": "Stop loss"})
            continue
        if is_sell(v):
            pending_sells.add(sym)

    # Buy signals for tomorrow
    avail = MAX_POS - len(positions) - len(pending_buys)
    if avail > 0:
        added = 0
        for sym, ss in signals.items():
            if added >= avail: break
            if sym in positions or sym in pending_buys: continue
            v = ss.get(day)
            if v and is_buy(v):
                pending_buys[sym] = day; added += 1

    # Portfolio value
    invested = sum(positions[s]["qty"] * (signals[s][day][C_] if day in signals.get(s, {})
                   else positions[s]["entry"]) for s in positions)
    port_val = cash + invested
    if port_val > equity_hi: equity_hi = port_val
    dd = (equity_hi - port_val) / equity_hi * 100
    if dd > max_dd: max_dd = dd
    equity_curve.append((day, port_val, cash, invested, len(positions)))

# Close open positions at final close
last = trading_days[-1]
for sym, pos in list(positions.items()):
    v = signals.get(sym, {}).get(last)
    px = v[C_] if v else pos["entry"]
    pnl = (px - pos["entry"]) * pos["qty"]
    cash += pos["qty"] * px
    trades.append({"sym": sym, "entry": pos["entry"], "exit": px, "qty": pos["qty"],
                   "entry_date": pos["date"], "exit_date": last, "pnl": pnl,
                   "pnl_pct": (px/pos["entry"]-1)*100,
                   "days": (pd.Timestamp(last)-pd.Timestamp(pos["date"])).days,
                   "reason": "Open at end"})
positions.clear()

final_value = cash
print(f"  Final portfolio value: ₹{final_value:,.0f}")
print(f"  Total trades: {len(trades)}")

# ─── Metrics ─────────────────────────────────────────────────────────────────
print("\nComputing analytics...")
years = len(trading_days) / 252
total_ret = (final_value / CAPITAL - 1) * 100
cagr      = ((final_value / CAPITAL) ** (1/years) - 1) * 100

# Daily returns of strategy
ec_vals  = np.array([e[1] for e in equity_curve])
strat_dr = ec_vals[1:] / ec_vals[:-1] - 1
# Nifty daily returns
nv = np.array([nifty_curve[d] for d in trading_days])
nifty_dr = nv[1:] / nv[:-1] - 1

ann_factor = 252
strat_vol  = np.std(strat_dr) * np.sqrt(ann_factor) * 100
nifty_vol  = np.std(nifty_dr) * np.sqrt(ann_factor) * 100

rf_daily = (1 + RISK_FREE/100) ** (1/ann_factor) - 1
# Sharpe
strat_sharpe = (np.mean(strat_dr) - rf_daily) / np.std(strat_dr) * np.sqrt(ann_factor) if np.std(strat_dr)>0 else 0
nifty_sharpe = (np.mean(nifty_dr) - rf_daily) / np.std(nifty_dr) * np.sqrt(ann_factor) if np.std(nifty_dr)>0 else 0
# Sortino
down_strat = strat_dr[strat_dr < 0]
down_nifty = nifty_dr[nifty_dr < 0]
strat_sortino = (np.mean(strat_dr) - rf_daily) / np.std(down_strat) * np.sqrt(ann_factor) if len(down_strat)>0 and np.std(down_strat)>0 else 0
nifty_sortino = (np.mean(nifty_dr) - rf_daily) / np.std(down_nifty) * np.sqrt(ann_factor) if len(down_nifty)>0 and np.std(down_nifty)>0 else 0
# Calmar
strat_calmar = cagr / max_dd if max_dd>0 else 0

# Beta / Alpha (CAPM) vs Nifty
cov = np.cov(strat_dr, nifty_dr)[0,1]
var_n = np.var(nifty_dr)
beta = cov / var_n if var_n>0 else 0
nifty_total = (nv[-1]/nv[0]-1)*100
nifty_cagr  = ((nv[-1]/nv[0])**(1/years)-1)*100
alpha = cagr - (RISK_FREE + beta*(nifty_cagr - RISK_FREE))   # annualized CAPM alpha
corr  = np.corrcoef(strat_dr, nifty_dr)[0,1]

# Nifty max DD
cmax=0; nifty_max_dd=0
for v in nv:
    if v>cmax: cmax=v
    d=(cmax-v)/cmax*100
    if d>nifty_max_dd: nifty_max_dd=d
nifty_calmar = nifty_cagr / nifty_max_dd if nifty_max_dd>0 else 0

# Drawdown series + longest DD duration
dd_series=[]; peak=ec_vals[0]; in_dd=False; dd_start=0; longest_dd=0
for i,v in enumerate(ec_vals):
    if v>peak: peak=v
    d=(peak-v)/peak*100
    dd_series.append(d)
# longest drawdown (days from peak to recovery)
peak=ec_vals[0]; peak_i=0; longest_dd_days=0
for i,v in enumerate(ec_vals):
    if v>=peak:
        peak=v; peak_i=i
    else:
        longest_dd_days=max(longest_dd_days, i-peak_i)

# Trade metrics
wins   = [t for t in trades if t["pnl"]>0]
losses = [t for t in trades if t["pnl"]<=0]
sl_hits= [t for t in trades if t["reason"]=="Stop loss"]
gross_profit = sum(t["pnl"] for t in wins)
gross_loss   = abs(sum(t["pnl"] for t in losses))
profit_factor= gross_profit/gross_loss if gross_loss>0 else 0
win_rate = 100*len(wins)/len(trades) if trades else 0
avg_win  = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
avg_loss = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
r_mult   = avg_win/abs(avg_loss) if avg_loss!=0 else 0
expectancy_pct = (win_rate/100)*avg_win + (1-win_rate/100)*avg_loss
largest_win  = max(trades, key=lambda t:t["pnl_pct"])
largest_loss = min(trades, key=lambda t:t["pnl_pct"])
avg_days = np.mean([t["days"] for t in trades]) if trades else 0
avg_win_days  = np.mean([t["days"] for t in wins]) if wins else 0
avg_loss_days = np.mean([t["days"] for t in losses]) if losses else 0

# ─── Tax (Indian FY Apr-Mar; STCG<365d=20%, LTCG≥365d=12.5% over ₹1.25L) ─────
def fy_of(dstr):
    d = pd.Timestamp(dstr)
    return d.year if d.month>=4 else d.year-1   # FY starting April
fy_buckets = {}
for t in trades:
    fy = fy_of(t["exit_date"])
    b = fy_buckets.setdefault(fy, {"stcg":0.0,"ltcg":0.0})
    if t["days"] >= 365: b["ltcg"] += t["pnl"]
    else:                b["stcg"] += t["pnl"]
total_tax=0.0; tax_rows=[]
for fy in sorted(fy_buckets):
    b=fy_buckets[fy]
    stcg_tax = STCG_RATE/100 * max(0.0, b["stcg"])
    ltcg_tax = LTCG_RATE/100 * max(0.0, b["ltcg"]-LTCG_EXEMPT)
    yr_tax = stcg_tax+ltcg_tax
    total_tax += yr_tax
    tax_rows.append((f"FY{fy}-{str(fy+1)[2:]}", b["stcg"], b["ltcg"], stcg_tax, ltcg_tax, yr_tax))
post_tax_value = final_value - total_tax
post_tax_ret   = (post_tax_value/CAPITAL-1)*100
post_tax_cagr  = ((post_tax_value/CAPITAL)**(1/years)-1)*100

# ─── Year-wise (calendar) MTM returns: strategy vs nifty ─────────────────────
year_rows=[]
ec_by_day = {e[0]: e[1] for e in equity_curve}
years_set = sorted(set(int(d[:4]) for d in trading_days))
for yr in years_set:
    yr_days = [d for d in trading_days if d[:4]==str(yr)]
    if not yr_days: continue
    s_start = ec_by_day[yr_days[0]]; s_end = ec_by_day[yr_days[-1]]
    # use prior year-end as base if available
    idx0 = trading_days.index(yr_days[0])
    base_s = ec_by_day[trading_days[idx0-1]] if idx0>0 else CAPITAL
    base_n = nifty_curve[trading_days[idx0-1]] if idx0>0 else nifty_curve[yr_days[0]]
    s_ret = (s_end/base_s-1)*100
    n_ret = (nifty_curve[yr_days[-1]]/base_n-1)*100
    # year DD for strategy
    yvals=[ec_by_day[d] for d in yr_days]; pk=yvals[0]; ydd=0
    for v in yvals:
        if v>pk: pk=v
        dd=(pk-v)/pk*100
        if dd>ydd: ydd=dd
    yr_closed = [t for t in trades if t["exit_date"][:4]==str(yr)]
    year_rows.append((yr, s_ret, n_ret, ydd, len(yr_closed)))

# Monthly returns matrix (strategy)
monthly = {}
prev_val = CAPITAL; prev_key=None
mser = {}
for d in trading_days:
    key = d[:7]  # YYYY-MM
    mser.setdefault(key, []).append(ec_by_day[d])
month_keys = sorted(mser.keys())
month_ret = {}
prev_end = CAPITAL
for i,mk in enumerate(month_keys):
    end_v = mser[mk][-1]
    base = prev_end
    month_ret[mk] = (end_v/base - 1)*100
    prev_end = end_v

print(f"  CAGR {cagr:.1f}% | Sharpe {strat_sharpe:.2f} | Sortino {strat_sortino:.2f} | "
      f"MaxDD {max_dd:.1f}% | Calmar {strat_calmar:.2f}")
print(f"  Win {win_rate:.1f}% | PF {profit_factor:.2f} | R-mult {r_mult:.2f} | "
      f"Beta {beta:.2f} | Alpha {alpha:.1f}%")
print(f"  Pre-tax ₹{final_value:,.0f} ({total_ret:+.1f}%) | Tax ₹{total_tax:,.0f} | "
      f"Post-tax ₹{post_tax_value:,.0f} ({post_tax_ret:+.1f}%)")

# Save raw bundle for the HTML generator
bundle = {
    "config": {"capital":CAPITAL,"sl_pct":SL_PCT,"max_pos":MAX_POS,"rpt":RPT,
               "fast_n":FAST_N,"slow_n":SLOW_N,"min_adt_cr":MIN_ADT_CR,
               "sim_start":str(SIM_START),"sim_end":str(SIM_END),
               "risk_free":RISK_FREE,"universe":len(signals),"currency":"INR","benchmark":"Nifty 50",
               "stcg_rate":STCG_RATE,"ltcg_rate":LTCG_RATE,"ltcg_exempt":LTCG_EXEMPT,
               "pos_value":pos_value},
    "summary": {
        "final_value":final_value,"total_ret":total_ret,"cagr":cagr,
        "post_tax_value":post_tax_value,"post_tax_ret":post_tax_ret,"post_tax_cagr":post_tax_cagr,
        "total_tax":total_tax,
        "max_dd":max_dd,"longest_dd_days":longest_dd_days,
        "vol":strat_vol,"sharpe":strat_sharpe,"sortino":strat_sortino,"calmar":strat_calmar,
        "beta":beta,"alpha":alpha,"corr":corr,
        "nifty_total":nifty_total,"nifty_cagr":nifty_cagr,"nifty_vol":nifty_vol,
        "nifty_sharpe":nifty_sharpe,"nifty_sortino":nifty_sortino,"nifty_max_dd":nifty_max_dd,
        "nifty_calmar":nifty_calmar,
        "trades":len(trades),"wins":len(wins),"losses":len(losses),"win_rate":win_rate,
        "avg_win":avg_win,"avg_loss":avg_loss,"r_mult":r_mult,"profit_factor":profit_factor,
        "expectancy_pct":expectancy_pct,"gross_profit":gross_profit,"gross_loss":gross_loss,
        "sl_hits":len(sl_hits),"sl_rate":100*len(sl_hits)/len(trades) if trades else 0,
        "avg_days":avg_days,"avg_win_days":avg_win_days,"avg_loss_days":avg_loss_days,
        "largest_win_pct":largest_win["pnl_pct"],"largest_win_sym":largest_win["sym"],
        "largest_loss_pct":largest_loss["pnl_pct"],"largest_loss_sym":largest_loss["sym"],
        "years":years,
    },
    "equity_curve":[(e[0],e[1],e[2],e[3],e[4]) for e in equity_curve],
    "nifty_curve":[(d,nifty_curve[d]) for d in trading_days],
    "dd_series":[(trading_days[i],dd_series[i]) for i in range(len(trading_days))],
    "trades":trades,
    "year_rows":year_rows,
    "tax_rows":tax_rows,
    "month_ret":month_ret,
}
with open("/tmp/final_sim_bundle_2015.pkl","wb") as f:
    pickle.dump(bundle, f)
print("\nSaved /tmp/final_sim_bundle_2015.pkl")
