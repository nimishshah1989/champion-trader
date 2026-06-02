"""
S&P 500 version of RS EMA50x200 strategy simulation.
Capital $10,000 | 10% stop | 15 positions | 0.5% risk | fractional shares
Benchmark: S&P 500 (^GSPC). US tax: LTCG 15%, STCG 24% (adjustable).
Outputs /tmp/sp500_sim_bundle.pkl
"""
import pickle, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from datetime import date

SIM_START=date(2021,1,1); SIM_END=date(2026,5,31)
CAPITAL=10_000.0
SL_PCT=10.0; RPT=0.5; MAX_POS=15
FAST_N=50; SLOW_N=200
RISK_FREE=4.5                  # ~US 10yr / T-bill blended for Sharpe
MIN_ADT_USD=20_000_000.0       # $20M mean daily turnover (all S&P500 easily pass)
# US capital gains (assumption — adjustable to investor bracket)
STCG_RATE=24.0                 # short-term taxed as ordinary income (mid/high bracket)
LTCG_RATE=15.0                 # long-term (>1yr) 15% bracket
LTCG_EXEMPT=0.0                # US has no flat LTCG exemption like India's 1.25L

CACHE="/tmp/sp500_cache.pkl"
cache=pickle.load(open(CACHE,"rb"))
bench_df=cache["nifty"]; stock_data=cache["stocks"]
print(f"Loaded {len(stock_data)} stocks + benchmark")

bench_close=bench_df["Close"]
if isinstance(bench_close,pd.DataFrame): bench_close=bench_close.iloc[:,0]

sim_start_dt=pd.Timestamp(SIM_START); sim_end_dt=pd.Timestamp(SIM_END)
bench_sim=bench_close[(bench_close.index>=sim_start_dt)&(bench_close.index<=sim_end_dt)]
trading_days=[d.strftime("%Y-%m-%d") for d in bench_sim.index]
bench_curve={d.strftime("%Y-%m-%d"):float(v) for d,v in zip(bench_sim.index,bench_sim.values)}
print(f"Sim: {trading_days[0]} -> {trading_days[-1]} ({len(trading_days)} days)")

def ema(s,n): return s.ewm(span=n,adjust=False).mean()
O_,H_,L_,C_,FP,SP,FC,SC_=range(8)

signals={}; warmup=max(SLOW_N+10,210)
for sym,df in stock_data.items():
    try:
        common=df.index.intersection(bench_close.index)
        if len(common)<warmup: continue
        sc=df.loc[common,"Close"].astype(float); so=df.loc[common,"Open"].astype(float)
        sh=df.loc[common,"High"].astype(float); sl_=df.loc[common,"Low"].astype(float)
        vol=df.loc[common,"Volume"].astype(float); nc=bench_close.loc[common].astype(float)
        sim_mask=(common>=sim_start_dt)&(common<=sim_end_dt)
        adt=(sc.loc[sim_mask]*vol.loc[sim_mask]).mean()
        if np.isnan(adt) or adt<MIN_ADT_USD: continue
        rs=sc/nc; fast=ema(rs,FAST_N); slow=ema(rs,SLOW_N)
        sig={}
        for i in range(warmup,len(common)):
            fc,scur,fp,sp=fast.iloc[i],slow.iloc[i],fast.iloc[i-1],slow.iloc[i-1]
            if any(np.isnan(v) for v in [fc,scur,fp,sp]): continue
            ds=common[i].strftime("%Y-%m-%d")
            if ds<str(SIM_START) or ds>str(SIM_END): continue
            sig[ds]=(float(so.iloc[i]),float(sh.iloc[i]),float(sl_.iloc[i]),float(sc.iloc[i]),
                     float(fp),float(sp),float(fc),float(scur))
        if sig: signals[sym]=sig
    except Exception: pass
print(f"Universe: {len(signals)} stocks (ADT >= ${MIN_ADT_USD/1e6:.0f}M)")

def is_buy(v): return v[FP]<=v[SP] and v[FC]>v[SC_]
def is_sell(v): return v[FP]>=v[SP] and v[FC]<v[SC_]

cash=CAPITAL; pos_value=CAPITAL*(RPT/100)/(SL_PCT/100)
positions={}; pending_buys={}; pending_sells=set()
equity_hi=CAPITAL; max_dd=0.0; trades=[]; equity_curve=[]

for day in trading_days:
    done=set()
    for sym in list(pending_sells):
        if sym not in positions: done.add(sym); continue
        v=signals.get(sym,{}).get(day)
        if v is None: done.add(sym); continue
        px=v[O_]; pos=positions.pop(sym); pnl=(px-pos["entry"])*pos["qty"]; cash+=pos["qty"]*px
        trades.append({"sym":sym,"entry":pos["entry"],"exit":px,"qty":pos["qty"],
            "entry_date":pos["date"],"exit_date":day,"pnl":pnl,"pnl_pct":(px/pos["entry"]-1)*100,
            "days":(pd.Timestamp(day)-pd.Timestamp(pos["date"])).days,"reason":"RS reversal"})
        done.add(sym)
    pending_sells-=done
    done=set()
    for sym in list(pending_buys.keys()):
        if len(positions)>=MAX_POS: break
        if sym in positions: done.add(sym); continue
        v=signals.get(sym,{}).get(day)
        if v is None or v[O_]<=0: done.add(sym); continue
        px=v[O_]; qty=pos_value/px  # fractional shares
        cost=qty*px
        if cost>cash: done.add(sym); continue
        cash-=cost; positions[sym]={"entry":px,"sl":px*(1-SL_PCT/100),"qty":qty,"date":day}
        done.add(sym)
    for sym in done: pending_buys.pop(sym,None)
    for sym in list(positions.keys()):
        v=signals.get(sym,{}).get(day)
        if v is None: continue
        pos=positions[sym]
        if v[L_]<=pos["sl"]:
            px=pos["sl"] if v[O_]>pos["sl"] else v[O_]
            pnl=(px-pos["entry"])*pos["qty"]; cash+=pos["qty"]*px; positions.pop(sym)
            trades.append({"sym":sym,"entry":pos["entry"],"exit":px,"qty":pos["qty"],
                "entry_date":pos["date"],"exit_date":day,"pnl":pnl,"pnl_pct":(px/pos["entry"]-1)*100,
                "days":(pd.Timestamp(day)-pd.Timestamp(pos["date"])).days,"reason":"Stop loss"}); continue
        if is_sell(v): pending_sells.add(sym)
    avail=MAX_POS-len(positions)-len(pending_buys)
    if avail>0:
        added=0
        for sym,ss in signals.items():
            if added>=avail: break
            if sym in positions or sym in pending_buys: continue
            v=ss.get(day)
            if v and is_buy(v): pending_buys[sym]=day; added+=1
    invested=sum(positions[s]["qty"]*(signals[s][day][C_] if day in signals.get(s,{}) else positions[s]["entry"]) for s in positions)
    port=cash+invested
    if port>equity_hi: equity_hi=port
    dd=(equity_hi-port)/equity_hi*100
    if dd>max_dd: max_dd=dd
    equity_curve.append((day,port,cash,invested,len(positions)))

last=trading_days[-1]
for sym,pos in list(positions.items()):
    v=signals.get(sym,{}).get(last); px=v[C_] if v else pos["entry"]
    pnl=(px-pos["entry"])*pos["qty"]; cash+=pos["qty"]*px
    trades.append({"sym":sym,"entry":pos["entry"],"exit":px,"qty":pos["qty"],
        "entry_date":pos["date"],"exit_date":last,"pnl":pnl,"pnl_pct":(px/pos["entry"]-1)*100,
        "days":(pd.Timestamp(last)-pd.Timestamp(pos["date"])).days,"reason":"Open at end"})
positions.clear()
final_value=cash
print(f"Final: ${final_value:,.0f} | trades: {len(trades)}")

# ── metrics (same as India version) ──
years=len(trading_days)/252
total_ret=(final_value/CAPITAL-1)*100
cagr=((final_value/CAPITAL)**(1/years)-1)*100
ecv=np.array([e[1] for e in equity_curve]); sdr=ecv[1:]/ecv[:-1]-1
nv=np.array([bench_curve[d] for d in trading_days]); ndr=nv[1:]/nv[:-1]-1
af=252; svol=np.std(sdr)*np.sqrt(af)*100; nvol=np.std(ndr)*np.sqrt(af)*100
rfd=(1+RISK_FREE/100)**(1/af)-1
ssh=(np.mean(sdr)-rfd)/np.std(sdr)*np.sqrt(af) if np.std(sdr)>0 else 0
nsh=(np.mean(ndr)-rfd)/np.std(ndr)*np.sqrt(af) if np.std(ndr)>0 else 0
ds_=sdr[sdr<0]; dn_=ndr[ndr<0]
sso=(np.mean(sdr)-rfd)/np.std(ds_)*np.sqrt(af) if len(ds_)>0 and np.std(ds_)>0 else 0
nso=(np.mean(ndr)-rfd)/np.std(dn_)*np.sqrt(af) if len(dn_)>0 and np.std(dn_)>0 else 0
scal=cagr/max_dd if max_dd>0 else 0
cov=np.cov(sdr,ndr)[0,1]; varn=np.var(ndr); beta=cov/varn if varn>0 else 0
ntot=(nv[-1]/nv[0]-1)*100; ncagr=((nv[-1]/nv[0])**(1/years)-1)*100
alpha=cagr-(RISK_FREE+beta*(ncagr-RISK_FREE)); corr=np.corrcoef(sdr,ndr)[0,1]
cm=0; nmdd=0
for v in nv:
    if v>cm: cm=v
    d=(cm-v)/cm*100
    if d>nmdd: nmdd=d
ncal=ncagr/nmdd if nmdd>0 else 0
peak=ecv[0]; pi=0; lddd=0
for i,v in enumerate(ecv):
    if v>=peak: peak=v; pi=i
    else: lddd=max(lddd,i-pi)
wins=[t for t in trades if t["pnl"]>0]; losses=[t for t in trades if t["pnl"]<=0]
slh=[t for t in trades if t["reason"]=="Stop loss"]
gp=sum(t["pnl"] for t in wins); gl=abs(sum(t["pnl"] for t in losses))
pf=gp/gl if gl>0 else 0; wr=100*len(wins)/len(trades) if trades else 0
aw=np.mean([t["pnl_pct"] for t in wins]) if wins else 0
al=np.mean([t["pnl_pct"] for t in losses]) if losses else 0
rmult=aw/abs(al) if al!=0 else 0; exp_=(wr/100)*aw+(1-wr/100)*al
lw=max(trades,key=lambda t:t["pnl_pct"]); ll=min(trades,key=lambda t:t["pnl_pct"])
ad=np.mean([t["days"] for t in trades]); awd=np.mean([t["days"] for t in wins]) if wins else 0
ald=np.mean([t["days"] for t in losses]) if losses else 0

def fy_of(ds):  # US tax year = calendar year
    return pd.Timestamp(ds).year
fb={}
for t in trades:
    b=fb.setdefault(fy_of(t["exit_date"]),{"stcg":0.0,"ltcg":0.0})
    if t["days"]>=365: b["ltcg"]+=t["pnl"]
    else: b["stcg"]+=t["pnl"]
ttax=0.0; trows=[]
for fy in sorted(fb):
    b=fb[fy]; st=STCG_RATE/100*max(0,b["stcg"]); lt=LTCG_RATE/100*max(0,b["ltcg"]-LTCG_EXEMPT)
    ttax+=st+lt; trows.append((f"{fy}",b["stcg"],b["ltcg"],st,lt,st+lt))
ptv=final_value-ttax; ptr=(ptv/CAPITAL-1)*100; ptc=((ptv/CAPITAL)**(1/years)-1)*100

ecd={e[0]:e[1] for e in equity_curve}; yrows=[]
for yr in sorted(set(int(d[:4]) for d in trading_days)):
    yd=[d for d in trading_days if d[:4]==str(yr)]
    if not yd: continue
    i0=trading_days.index(yd[0]); bs=ecd[trading_days[i0-1]] if i0>0 else CAPITAL
    bn=bench_curve[trading_days[i0-1]] if i0>0 else bench_curve[yd[0]]
    sr=(ecd[yd[-1]]/bs-1)*100; nr=(bench_curve[yd[-1]]/bn-1)*100
    yv=[ecd[d] for d in yd]; pk=yv[0]; ydd=0
    for v in yv:
        if v>pk: pk=v
        dd=(pk-v)/pk*100
        if dd>ydd: ydd=dd
    yrows.append((yr,sr,nr,ydd,len([t for t in trades if t["exit_date"][:4]==str(yr)])))

mser={}
for d in trading_days: mser.setdefault(d[:7],[]).append(ecd[d])
mret={}; pe=CAPITAL
for mk in sorted(mser.keys()):
    ev=mser[mk][-1]; mret[mk]=(ev/pe-1)*100; pe=ev

print(f"CAGR {cagr:.1f}% (Nifty/SPX {ncagr:.1f}%) | Sharpe {ssh:.2f} | MaxDD {max_dd:.1f}% | "
      f"Alpha {alpha:+.1f}% | Win {wr:.1f}% | AvgWin {aw:+.1f}% | PF {pf:.2f}")
print(f"Pre-tax ${final_value:,.0f} ({total_ret:+.0f}%) | Tax ${ttax:,.0f} | Post-tax ${ptv:,.0f} ({ptr:+.0f}%)")

bundle={
 "config":{"capital":CAPITAL,"sl_pct":SL_PCT,"max_pos":MAX_POS,"rpt":RPT,"fast_n":FAST_N,"slow_n":SLOW_N,
   "min_adt_cr":MIN_ADT_USD/1e6,"sim_start":str(SIM_START),"sim_end":str(SIM_END),"risk_free":RISK_FREE,
   "universe":len(signals),"stcg_rate":STCG_RATE,"ltcg_rate":LTCG_RATE,"ltcg_exempt":LTCG_EXEMPT,
   "pos_value":pos_value,"currency":"USD","benchmark":"S&P 500","adt_unit":"M"},
 "summary":{"final_value":final_value,"total_ret":total_ret,"cagr":cagr,"post_tax_value":ptv,
   "post_tax_ret":ptr,"post_tax_cagr":ptc,"total_tax":ttax,"max_dd":max_dd,"longest_dd_days":lddd,
   "vol":svol,"sharpe":ssh,"sortino":sso,"calmar":scal,"beta":beta,"alpha":alpha,"corr":corr,
   "nifty_total":ntot,"nifty_cagr":ncagr,"nifty_vol":nvol,"nifty_sharpe":nsh,"nifty_sortino":nso,
   "nifty_max_dd":nmdd,"nifty_calmar":ncal,"trades":len(trades),"wins":len(wins),"losses":len(losses),
   "win_rate":wr,"avg_win":aw,"avg_loss":al,"r_mult":rmult,"profit_factor":pf,"expectancy_pct":exp_,
   "gross_profit":gp,"gross_loss":gl,"sl_hits":len(slh),"sl_rate":100*len(slh)/len(trades) if trades else 0,
   "avg_days":ad,"avg_win_days":awd,"avg_loss_days":ald,"largest_win_pct":lw["pnl_pct"],
   "largest_win_sym":lw["sym"],"largest_loss_pct":ll["pnl_pct"],"largest_loss_sym":ll["sym"],"years":years},
 "equity_curve":[(e[0],e[1],e[2],e[3],e[4]) for e in equity_curve],
 "nifty_curve":[(d,bench_curve[d]) for d in trading_days],
 "dd_series":None,"trades":trades,"year_rows":yrows,"tax_rows":trows,"month_ret":mret,
}
# drawdown series
dds=[]; pk=ecv[0]
for i,v in enumerate(ecv):
    if v>pk: pk=v
    dds.append((trading_days[i],(pk-v)/pk*100))
bundle["dd_series"]=dds
pickle.dump(bundle, open("/tmp/sp500_sim_bundle.pkl","wb"))
print("Saved /tmp/sp500_sim_bundle.pkl")
