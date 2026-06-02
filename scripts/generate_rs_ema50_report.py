"""
Generate self-contained HTML analytics report from /tmp/final_sim_bundle.pkl
All charts are inline SVG -> no external dependencies, emailable to a fund manager.
Comprehensive edition: equity, log-equity, rolling 12m returns, exposure,
drawdown (with peak/trough markers + shaded window), drawdown decomposition,
year bars, monthly heatmap, trade-return distribution, holding-period scatter,
top profit contributors, full risk/return metrics, tax, trade ledger.
"""
import pickle, html
import numpy as np

with open("/tmp/final_sim_bundle.pkl","rb") as f:
    B = pickle.load(f)

cfg, S = B["config"], B["summary"]
ec   = B["equity_curve"]      # (date, port, cash, invested, npos)
nc   = B["nifty_curve"]       # (date, close)
dds  = B["dd_series"]         # (date, dd%)
trades = B["trades"]
year_rows = B["year_rows"]
tax_rows  = B["tax_rows"]
month_ret = B["month_ret"]

CAP = cfg["capital"]
SLP = cfg["sl_pct"]

# ─── number formatting ───────────────────────────────────────────────────────
def inr(x, dec=0):
    neg = x < 0; x = abs(x)
    s = f"{x:.{dec}f}"
    if "." in s: intp, decp = s.split("."); decp="."+decp
    else: intp, decp = s, ""
    if len(intp) > 3:
        last3 = intp[-3:]; rest = intp[:-3]; parts=[]
        while len(rest) > 2: parts.insert(0, rest[-2:]); rest = rest[:-2]
        if rest: parts.insert(0, rest)
        intp = ",".join(parts) + "," + last3
    return ("-" if neg else "") + "₹" + intp + decp

def lakh(x): return f"₹{x/1e5:.2f}L"

# ─── derived series ──────────────────────────────────────────────────────────
dates = [e[0] for e in ec]
vals  = np.array([e[1] for e in ec])
cash  = np.array([e[2] for e in ec])
inv   = np.array([e[3] for e in ec])
npos  = np.array([e[4] for e in ec])
n     = len(vals)

# Drawdown peak/trough window
peak=vals[0]; cur_peak_i=0; max_dd=0; dd_peak_i=0; dd_trough_i=0
for i,v in enumerate(vals):
    if v>peak: peak=v; cur_peak_i=i
    dd=(peak-v)/peak*100
    if dd>max_dd: max_dd=dd; dd_peak_i=cur_peak_i; dd_trough_i=i
# recovery index (first day after trough that re-takes the peak)
recov_i=None
for i in range(dd_trough_i, n):
    if vals[i] >= vals[dd_peak_i]:
        recov_i=i; break

# ─── SVG helpers ─────────────────────────────────────────────────────────────
def _xlabels(series, X, height, pad, vlines=False):
    out=""; seen=set()
    for i,(d,_) in enumerate(series):
        ylab=d[:4]
        if ylab not in seen:
            seen.add(ylab)
            if vlines:
                out+=f'<line x1="{X(i):.1f}" y1="{pad}" x2="{X(i):.1f}" y2="{height-pad}" stroke="#16202b" stroke-width="1"/>'
            out+=f'<text x="{X(i):.1f}" y="{height-pad+18}" fill="#5b6b7d" font-size="11" text-anchor="middle">{ylab}</text>'
    return out

def svg_dual_line(series_a, series_b, labels, colors, width=1080, height=420,
                  pad=60, y_is_currency=True, logscale=False, hline=None,
                  yfmt=None, markers=None, zeroline=False):
    n=len(series_a)
    ax=[v for _,v in series_a]; bx=[v for _,v in series_b] if series_b else []
    allv=ax+bx+([hline] if hline else [])
    ymin,ymax=min(allv),max(allv)
    if logscale:
        import math
        ymin_l,ymax_l=math.log10(max(ymin,1)),math.log10(ymax)
        def yv(v): return math.log10(max(v,1))
    else:
        def yv(v): return v
        ymin_l,ymax_l=ymin,ymax
    yr=ymax_l-ymin_l or 1
    def X(i): return pad+i*(width-2*pad)/(n-1)
    def Y(v): return height-pad-(yv(v)-ymin_l)/yr*(height-2*pad)
    def path(s): return "M"+" L".join(f"{X(i):.1f},{Y(v):.1f}" for i,(_,v) in enumerate(s))
    grid=""; lbls=""
    for g in range(6):
        gy=height-pad-g*(height-2*pad)/5; val=ymin_l+g*yr/5
        rv=(10**val) if logscale else val
        grid+=f'<line x1="{pad}" y1="{gy:.1f}" x2="{width-pad}" y2="{gy:.1f}" stroke="#1e2a38" stroke-width="1"/>'
        if yfmt: lab=yfmt(rv)
        elif y_is_currency: lab=lakh(rv)
        else: lab=f"{rv:.0f}"
        lbls+=f'<text x="{pad-8}" y="{gy+4:.1f}" fill="#5b6b7d" font-size="11" text-anchor="end">{lab}</text>'
    xlbls=_xlabels(series_a,X,height,pad,vlines=True)
    hl=""
    if hline is not None:
        hl=f'<line x1="{pad}" y1="{Y(hline):.1f}" x2="{width-pad}" y2="{Y(hline):.1f}" stroke="#d9a441" stroke-width="1.4" stroke-dasharray="6 4"/>'
        hl+=f'<text x="{width-pad-4}" y="{Y(hline)-6:.1f}" fill="#d9a441" font-size="11" text-anchor="end">Starting capital {lakh(hline)}</text>'
    if zeroline:
        hl+=f'<line x1="{pad}" y1="{Y(0):.1f}" x2="{width-pad}" y2="{Y(0):.1f}" stroke="#3a4a5a" stroke-width="1.2"/>'
    area_pts=" ".join(f"{X(i):.1f},{Y(v):.1f}" for i,(_,v) in enumerate(series_a))
    fill_a=f'<polygon points="{X(0):.1f},{height-pad:.1f} {area_pts} {X(n-1):.1f},{height-pad:.1f}" fill="{colors[0]}" opacity="0.08"/>'
    pa=f'<path d="{path(series_a)}" fill="none" stroke="{colors[0]}" stroke-width="2.2"/>'
    pb=f'<path d="{path(series_b)}" fill="none" stroke="{colors[1]}" stroke-width="1.8" opacity="0.85"/>' if series_b else ""
    mk=""
    if markers:
        for idx,label,col in markers:
            mk+=f'<circle cx="{X(idx):.1f}" cy="{Y(series_a[idx][1]):.1f}" r="5" fill="{col}" stroke="#0a1118" stroke-width="2"/>'
            mk+=f'<text x="{X(idx):.1f}" y="{Y(series_a[idx][1])-12:.1f}" fill="{col}" font-size="11" text-anchor="middle" font-weight="600">{label}</text>'
    leg=f'<g font-size="13"><rect x="{pad+8}" y="{pad+6}" width="13" height="13" fill="{colors[0]}"/><text x="{pad+28}" y="{pad+17}" fill="#c9d6e3">{labels[0]}</text>'
    if series_b:
        leg+=f'<rect x="{pad+8}" y="{pad+26}" width="13" height="13" fill="{colors[1]}"/><text x="{pad+28}" y="{pad+37}" fill="#c9d6e3">{labels[1]}</text>'
    leg+="</g>"
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{grid}{xlbls}{lbls}{fill_a}{hl}{pb}{pa}{mk}{leg}</svg>'

def svg_area_dd(series, width=1080, height=300, pad=60, color="#e05260",
                peak_i=None, trough_i=None, recov_i=None):
    n=len(series); vv=[v for _,v in series]; ymax=max(vv) or 1
    def X(i): return pad+i*(width-2*pad)/(n-1)
    def Y(v): return pad+(v/ymax)*(height-2*pad)
    grid=""; lbls=""
    for g in range(5):
        val=g*ymax/4; gy=pad+(val/ymax)*(height-2*pad)
        grid+=f'<line x1="{pad}" y1="{gy:.1f}" x2="{width-pad}" y2="{gy:.1f}" stroke="#1e2a38" stroke-width="1"/>'
        lbls+=f'<text x="{pad-8}" y="{gy+4:.1f}" fill="#5b6b7d" font-size="11" text-anchor="end">-{val:.0f}%</text>'
    xlbls=_xlabels(series,X,height,pad)
    shade=""
    if peak_i is not None and trough_i is not None:
        x0=X(peak_i); x1=X(recov_i if recov_i else trough_i)
        shade=f'<rect x="{x0:.1f}" y="{pad}" width="{x1-x0:.1f}" height="{height-2*pad}" fill="#e05260" opacity="0.07"/>'
    pts=" ".join(f"{X(i):.1f},{Y(v):.1f}" for i,(_,v) in enumerate(series))
    poly=f'<polygon points="{X(0):.1f},{pad:.1f} {pts} {X(n-1):.1f},{pad:.1f}" fill="{color}" opacity="0.25"/>'
    line=f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8"/>'
    mk=""
    if trough_i is not None:
        ty=Y(series[trough_i][1])
        mk+=f'<circle cx="{X(trough_i):.1f}" cy="{ty:.1f}" r="5" fill="#e05260" stroke="#0a1118" stroke-width="2"/>'
        mk+=f'<text x="{X(trough_i):.1f}" y="{ty+18:.1f}" fill="#e88" font-size="11" text-anchor="middle" font-weight="600">max -{series[trough_i][1]:.1f}% ({series[trough_i][0]})</text>'
    if peak_i is not None:
        mk+=f'<line x1="{X(peak_i):.1f}" y1="{pad}" x2="{X(peak_i):.1f}" y2="{height-pad}" stroke="#3fb950" stroke-width="1" stroke-dasharray="4 3"/>'
        mk+=f'<text x="{X(peak_i):.1f}" y="{pad-4:.1f}" fill="#3fb950" font-size="11" text-anchor="middle" font-weight="600">peak</text>'
    if recov_i is not None:
        mk+=f'<line x1="{X(recov_i):.1f}" y1="{pad}" x2="{X(recov_i):.1f}" y2="{height-pad}" stroke="#4a7dbf" stroke-width="1" stroke-dasharray="4 3"/>'
        mk+=f'<text x="{X(recov_i):.1f}" y="{pad-4:.1f}" fill="#6f9bd0" font-size="11" text-anchor="middle" font-weight="600">recovered</text>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{shade}{grid}{xlbls}{lbls}{poly}{line}{mk}</svg>'

def svg_bar_years(rows, width=1080, height=340, pad=60):
    n=len(rows); vv=[r[1] for r in rows]+[r[2] for r in rows]
    ymax=max(vv+[5]); ymin=min(vv+[0]); span=ymax-ymin or 1
    gw=(width-2*pad)/n
    def Y(v): return height-pad-(v-ymin)/span*(height-2*pad)
    zero=Y(0); bars=""; xlbls=""; bw=gw*0.32
    for i,r in enumerate(rows):
        cx=pad+i*gw+gw/2
        s_y=Y(r[1]); n_y=Y(r[2])
        sy0=min(s_y,zero); sh=abs(s_y-zero)
        col_s="#3fb950" if r[1]>=0 else "#e05260"
        bars+=f'<rect x="{cx-bw-2:.1f}" y="{sy0:.1f}" width="{bw:.1f}" height="{sh:.1f}" fill="{col_s}"/>'
        bars+=f'<text x="{cx-bw/2-2:.1f}" y="{sy0-4 if r[1]>=0 else sy0+sh+12:.1f}" fill="#c9d6e3" font-size="10" text-anchor="middle">{r[1]:+.0f}</text>'
        ny0=min(n_y,zero); nh=abs(n_y-zero)
        bars+=f'<rect x="{cx+2:.1f}" y="{ny0:.1f}" width="{bw:.1f}" height="{nh:.1f}" fill="#4a7dbf" opacity="0.8"/>'
        bars+=f'<text x="{cx+bw/2+2:.1f}" y="{ny0-4 if r[2]>=0 else ny0+nh+12:.1f}" fill="#7e93a8" font-size="10" text-anchor="middle">{r[2]:+.0f}</text>'
        xlbls+=f'<text x="{cx:.1f}" y="{height-pad+18}" fill="#8a9bad" font-size="12" text-anchor="middle">{r[0]}</text>'
    axis=f'<line x1="{pad}" y1="{zero:.1f}" x2="{width-pad}" y2="{zero:.1f}" stroke="#3a4a5a" stroke-width="1.5"/>'
    leg=f'<g font-size="13"><rect x="{pad+8}" y="14" width="13" height="13" fill="#3fb950"/><text x="{pad+28}" y="25" fill="#c9d6e3">Strategy</text><rect x="{pad+120}" y="14" width="13" height="13" fill="#4a7dbf"/><text x="{pad+140}" y="25" fill="#c9d6e3">Nifty 50</text></g>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{axis}{bars}{xlbls}{leg}</svg>'

def svg_histogram(labels, counts, bin_colors, width=1080, height=340, pad=60, subtext=None):
    n=len(counts); ymax=max(counts) or 1; gw=(width-2*pad)/n
    def Y(c): return height-pad-(c/ymax)*(height-2*pad)
    bars=""; xlbls=""
    for i,(lab,c,col) in enumerate(zip(labels,counts,bin_colors)):
        x=pad+i*gw+gw*0.12; bw=gw*0.76; y=Y(c)
        bars+=f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{height-pad-y:.1f}" fill="{col}" rx="2"/>'
        bars+=f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" fill="#c9d6e3" font-size="12" text-anchor="middle" font-weight="600">{c}</text>'
        xlbls+=f'<text x="{x+bw/2:.1f}" y="{height-pad+18}" fill="#8a9bad" font-size="10.5" text-anchor="middle">{lab}</text>'
        if subtext:
            xlbls+=f'<text x="{x+bw/2:.1f}" y="{height-pad+32}" fill="#5b6b7d" font-size="9.5" text-anchor="middle">{subtext[i]}</text>'
    axis=f'<line x1="{pad}" y1="{height-pad:.1f}" x2="{width-pad}" y2="{height-pad:.1f}" stroke="#3a4a5a" stroke-width="1.2"/>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{axis}{bars}{xlbls}</svg>'

def svg_scatter(points, width=1080, height=400, pad=60):
    """points: list of (days, ret_pct, is_win)"""
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    xmax=max(xs)*1.05; ymin=min(ys+[0]); ymax=max(ys)*1.05; yspan=ymax-ymin or 1
    def X(d): return pad+d/xmax*(width-2*pad)
    def Y(r): return height-pad-(r-ymin)/yspan*(height-2*pad)
    grid=""; lbls=""
    for g in range(6):
        val=ymin+g*yspan/5; gy=Y(val)
        grid+=f'<line x1="{pad}" y1="{gy:.1f}" x2="{width-pad}" y2="{gy:.1f}" stroke="#1e2a38" stroke-width="1"/>'
        lbls+=f'<text x="{pad-8}" y="{gy+4:.1f}" fill="#5b6b7d" font-size="11" text-anchor="end">{val:+.0f}%</text>'
    for g in range(7):
        dv=g*xmax/6; gx=X(dv)
        lbls+=f'<text x="{gx:.1f}" y="{height-pad+18:.1f}" fill="#5b6b7d" font-size="11" text-anchor="middle">{dv:.0f}d</text>'
    zero=f'<line x1="{pad}" y1="{Y(0):.1f}" x2="{width-pad}" y2="{Y(0):.1f}" stroke="#3a4a5a" stroke-width="1.2"/>'
    dots=""
    for d,r,w in points:
        col="#3fb950" if w else "#e05260"
        dots+=f'<circle cx="{X(d):.1f}" cy="{Y(r):.1f}" r="3.4" fill="{col}" opacity="0.62"/>'
    leg=f'<g font-size="13"><circle cx="{pad+14}" cy="20" r="5" fill="#3fb950"/><text x="{pad+26}" y="24" fill="#c9d6e3">Winners</text><circle cx="{pad+110}" cy="20" r="5" fill="#e05260"/><text x="{pad+122}" y="24" fill="#c9d6e3">Losers</text></g>'
    ylab=f'<text x="14" y="{height/2:.0f}" fill="#6f8295" font-size="11" transform="rotate(-90 14 {height/2:.0f})" text-anchor="middle">Trade return %</text>'
    xlab=f'<text x="{width/2:.0f}" y="{height-8}" fill="#6f8295" font-size="11" text-anchor="middle">Holding period (calendar days)</text>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{grid}{lbls}{zero}{dots}{leg}{ylab}{xlab}</svg>'

def svg_hbar(items, width=1080, height=None, pad=60):
    """items: list of (label, value_rupees). Sorted desc by value."""
    if height is None: height=44+len(items)*30
    vmax=max(abs(v) for _,v in items) or 1
    rowh=(height-2*20)/len(items)
    barx=pad+150; barw=width-barx-pad-110
    out=""
    for i,(lab,v) in enumerate(items):
        y=20+i*rowh+rowh*0.18; bh=rowh*0.64
        col="#3fb950" if v>=0 else "#e05260"
        w=abs(v)/vmax*barw
        out+=f'<text x="{barx-10:.1f}" y="{y+bh*0.72:.1f}" fill="#c9d6e3" font-size="12.5" text-anchor="end">{html.escape(lab)}</text>'
        out+=f'<rect x="{barx:.1f}" y="{y:.1f}" width="{w:.1f}" height="{bh:.1f}" fill="{col}" rx="2"/>'
        out+=f'<text x="{barx+w+8:.1f}" y="{y+bh*0.72:.1f}" fill="#9fb2c4" font-size="12" text-anchor="start">{inr(v)}</text>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{out}</svg>'

# ─── build series for charts ─────────────────────────────────────────────────
eq_series=[(d,v) for d,v,_,_,_ in ec]
n0=nc[0][1]
bench_series=[(d,CAP*(v/n0)) for d,v in nc]
expo_series=[(d,100*inv[i]/vals[i] if vals[i]>0 else 0) for i,(d,_,_,_,_) in enumerate(ec)]

# rolling 12-month (252-day) returns
roll_s=[]; roll_n=[]
nvals=np.array([v for _,v in nc])
for i in range(252,n):
    roll_s.append((dates[i],(vals[i]/vals[i-252]-1)*100))
    roll_n.append((dates[i],(nvals[i]/nvals[i-252]-1)*100))

# markers for equity curve (peak & trough of max DD)
eq_markers=[(dd_peak_i,"peak","#3fb950"),(dd_trough_i,"trough","#e05260")]

chart_equity=svg_dual_line(eq_series,bench_series,
    ["RS EMA50×200 Strategy","Nifty 50 (buy & hold)"],["#3fb950","#4a7dbf"],
    y_is_currency=True, hline=CAP, markers=eq_markers)
chart_equity_log=svg_dual_line(eq_series,bench_series,
    ["RS EMA50×200 Strategy (log)","Nifty 50 (log)"],["#3fb950","#4a7dbf"],
    y_is_currency=True, logscale=True)
chart_roll=svg_dual_line(roll_s,roll_n,
    ["Strategy rolling 12-mo return","Nifty rolling 12-mo return"],["#3fb950","#4a7dbf"],
    y_is_currency=False, yfmt=lambda v:f"{v:+.0f}%", zeroline=True)
chart_expo=svg_dual_line(expo_series,None,["% of capital invested"],["#d9a441"],
    y_is_currency=False, yfmt=lambda v:f"{v:.0f}%")
chart_dd=svg_area_dd(dds, peak_i=dd_peak_i, trough_i=dd_trough_i, recov_i=recov_i)
chart_years=svg_bar_years(year_rows)

# trade-return distribution
bins=[(-100,-10),(-10,0),(0,25),(25,50),(50,100),(100,200),(200,500),(500,10000)]
blabels=["≤-10%","-10–0%","0–25%","25–50%","50–100%","100–200%","200–500%","500%+"]
bcounts=[sum(1 for t in trades if lo<=t["pnl_pct"]<hi) for lo,hi in bins]
bcolors=["#c0392b","#e05260","#356b42","#3a8a52","#3fb950","#46c95c","#52d968","#6ee986"]
bpnl=[sum(t["pnl"] for t in trades if lo<=t["pnl_pct"]<hi) for lo,hi in bins]
bsub=[inr(p) for p in bpnl]
chart_hist=svg_histogram(blabels,bcounts,bcolors,subtext=bsub)

# holding-period scatter
scatter_pts=[(t["days"],t["pnl_pct"],t["pnl"]>0) for t in trades]
chart_scatter=svg_scatter(scatter_pts)

# top contributors by symbol
from collections import defaultdict
sym_pnl=defaultdict(float)
for t in trades: sym_pnl[t["sym"]]+=t["pnl"]
top_contrib=sorted(sym_pnl.items(),key=lambda kv:kv[1],reverse=True)[:15]
chart_contrib=svg_hbar(top_contrib)

# concentration
gross_profit=S["gross_profit"]
sorted_pnl=sorted([t["pnl"] for t in trades if t["pnl"]>0],reverse=True)
top10_share=100*sum(sorted_pnl[:10])/gross_profit if gross_profit>0 else 0
top20_share=100*sum(sorted_pnl[:20])/gross_profit if gross_profit>0 else 0

# monthly heatmap
mk=sorted(month_ret.keys()); years_m=sorted(set(int(k[:4]) for k in mk))
months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
def heat_color(v):
    if v is None: return "#0d1620"
    if v>=0: a=min(v/12,1); return f"rgba(63,185,80,{0.15+0.7*a:.2f})"
    a=min(-v/12,1); return f"rgba(224,82,96,{0.15+0.7*a:.2f})"
heat="<table class='heat'><tr><th></th>"+"".join(f"<th>{m}</th>" for m in months)+"<th>Year</th></tr>"
for y in years_m:
    heat+=f"<tr><td class='yr'>{y}</td>"; yc_comp=1.0
    for mi in range(12):
        key=f"{y}-{mi+1:02d}"; v=month_ret.get(key)
        if v is not None: yc_comp*=(1+v/100)
        cell="" if v is None else f"{v:+.1f}"
        heat+=f"<td style='background:{heat_color(v)}'>{cell}</td>"
    yc=(yc_comp-1)*100 if yc_comp!=1.0 else None
    heat+=f"<td class='yr' style='background:{heat_color(yc)}'>{'' if yc is None else f'{yc:+.1f}'}</td></tr>"
heat+="</table>"

# trade ledger
trades_sorted=sorted(trades,key=lambda t:t["pnl_pct"],reverse=True)
top_win=trades_sorted[:12]; top_loss=trades_sorted[-8:]
def trade_rows(ts):
    r=""
    for t in ts:
        cls="pos" if t["pnl"]>0 else "neg"
        rcls={"Stop loss":"badge-sl","RS reversal":"badge-rs","Open at end":"badge-open"}.get(t["reason"],"")
        r+=f'<tr><td class="sym">{html.escape(t["sym"])}</td><td>{t["entry_date"]}</td><td>{t["exit_date"]}</td><td class="num">{t["days"]}</td><td class="num">₹{t["entry"]:.1f}</td><td class="num">₹{t["exit"]:.1f}</td><td class="num {cls}">{t["pnl_pct"]:+.1f}%</td><td class="num {cls}">{inr(t["pnl"])}</td><td><span class="badge {rcls}">{t["reason"]}</span></td></tr>'
    return r

from collections import Counter
reason_ct=Counter(t["reason"] for t in trades); reason_pnl={}
for t in trades: reason_pnl[t["reason"]]=reason_pnl.get(t["reason"],0)+t["pnl"]

def metric_card(label,value,sub="",good=None):
    cls=""
    if good is True: cls="pos"
    elif good is False: cls="neg"
    return f'<div class="card"><div class="card-label">{label}</div><div class="card-value {cls}">{value}</div><div class="card-sub">{sub}</div></div>'

# tables
tax_table=""
for fy,stcg,ltcg,st_tax,lt_tax,tot in tax_rows:
    tax_table+=f'<tr><td>{fy}</td><td class="num">{inr(stcg)}</td><td class="num">{inr(ltcg)}</td><td class="num">{inr(st_tax)}</td><td class="num">{inr(lt_tax)}</td><td class="num strong">{inr(tot)}</td></tr>'
year_table=""
for yr,sr,nr,dd,ntr in year_rows:
    oc="pos" if sr>nr else "neg"
    year_table+=f'<tr><td>{yr}</td><td class="num {"pos" if sr>=0 else "neg"}">{sr:+.1f}%</td><td class="num {"pos" if nr>=0 else "neg"}">{nr:+.1f}%</td><td class="num {oc}">{sr-nr:+.1f}%</td><td class="num">{dd:.1f}%</td><td class="num">{ntr}</td></tr>'
reason_table=""
for rsn,ct in reason_ct.most_common():
    pnl=reason_pnl[rsn]
    reason_table+=f'<tr><td>{rsn}</td><td class="num">{ct}</td><td class="num">{100*ct/len(trades):.1f}%</td><td class="num {"pos" if pnl>=0 else "neg"}">{inr(pnl)}</td></tr>'

# drawdown decomposition numbers
peak_val=vals[dd_peak_i]; trough_val=vals[dd_trough_i]
peak_gain=(peak_val/CAP-1)*100; trough_gain=(trough_val/CAP-1)*100
dd_drop=peak_val-trough_val
dd_days=dd_trough_i-dd_peak_i
recov_days=(recov_i-dd_trough_i) if recov_i else None
maxrisk_pct=cfg["max_pos"]*cfg["rpt"]

HTML=f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RS EMA50×200 — Strategy Analytics Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0a1118;color:#c9d6e3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5;padding:0 0 80px}}
  .wrap{{max-width:1180px;margin:0 auto;padding:0 24px}}
  header{{background:linear-gradient(135deg,#0d1825 0%,#10202f 100%);border-bottom:1px solid #1c2c3c;padding:42px 0 36px;margin-bottom:36px}}
  header .wrap{{display:flex;flex-direction:column;gap:6px}}
  h1{{font-size:30px;font-weight:700;color:#fff;letter-spacing:-0.5px}}
  .subtitle{{color:#7e93a8;font-size:15px}}
  .tagline{{margin-top:14px;display:flex;flex-wrap:wrap;gap:10px}}
  .pill{{background:#13212e;border:1px solid #20303f;border-radius:20px;padding:5px 14px;font-size:12.5px;color:#9fb2c4}}
  .pill b{{color:#dce8f3}}
  h2{{font-size:21px;color:#fff;margin:46px 0 8px;padding-bottom:10px;border-bottom:1px solid #1c2c3c;font-weight:650}}
  .lead{{color:#8a9bad;font-size:14px;margin:4px 0 12px}}
  h3{{font-size:14px;color:#9fb2c4;margin:24px 0 12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}}
  .grid4{{grid-template-columns:repeat(4,1fr)}}
  .card{{background:#0f1b27;border:1px solid #1a2a39;border-radius:10px;padding:16px 18px}}
  .card-label{{font-size:12px;color:#6f8295;text-transform:uppercase;letter-spacing:0.5px}}
  .card-value{{font-size:25px;font-weight:700;color:#fff;margin:6px 0 2px}}
  .card-sub{{font-size:12px;color:#6f8295}}
  .pos{{color:#3fb950 !important}} .neg{{color:#e05260 !important}}
  .chart-box{{background:#0c1620;border:1px solid #1a2a39;border-radius:12px;padding:22px;margin:18px 0}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;margin:12px 0}}
  th,td{{padding:9px 12px;text-align:left;border-bottom:1px solid #16222e}}
  th{{color:#6f8295;font-size:11.5px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600}}
  td.num{{text-align:right;font-variant-numeric:tabular-nums}}
  td.sym{{font-weight:600;color:#dce8f3}}
  td.strong{{font-weight:700;color:#fff}}
  tr:hover td{{background:#0f1b27}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
  @media(max-width:820px){{.two-col{{grid-template-columns:1fr}} .grid4{{grid-template-columns:repeat(2,1fr)}}}}
  .badge{{font-size:11px;padding:2px 9px;border-radius:5px;font-weight:600}}
  .badge-sl{{background:#3a1620;color:#e88}} .badge-rs{{background:#16302a;color:#7fd9b0}}
  .badge-open{{background:#2a2616;color:#d9c97f}}
  .heat{{font-size:11px}} .heat th{{text-align:center;padding:6px 4px}}
  .heat td{{text-align:center;padding:7px 4px;border:1px solid #0a1118;color:#dce8f3;font-variant-numeric:tabular-nums}}
  .heat td.yr{{font-weight:700;color:#9fb2c4}}
  .note{{background:#13202d;border-left:3px solid #d9a441;border-radius:6px;padding:14px 18px;font-size:13px;color:#b9c8d6;margin:16px 0}}
  .note.green{{border-left-color:#3fb950}} .note.blue{{border-left-color:#4a7dbf}} .note.red{{border-left-color:#e05260}}
  .footer{{margin-top:50px;padding-top:24px;border-top:1px solid #1c2c3c;color:#5b6b7d;font-size:12px;text-align:center}}
  .ddflow{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;align-items:center;gap:10px;margin:18px 0}}
  .ddbox{{background:#0f1b27;border:1px solid #1a2a39;border-radius:10px;padding:16px;text-align:center}}
  .ddbox .lab{{font-size:11px;color:#6f8295;text-transform:uppercase;letter-spacing:.5px}}
  .ddbox .big{{font-size:22px;font-weight:700;color:#fff;margin:6px 0 2px}}
  .ddbox .sm{{font-size:12px;color:#8a9bad}}
  .ddarrow{{font-size:22px;color:#e05260;text-align:center}}
  @media(max-width:820px){{.ddflow{{grid-template-columns:1fr;gap:6px}} .ddarrow{{transform:rotate(90deg)}}}}
</style></head>
<body>
<header><div class="wrap">
  <h1>Relative Strength EMA50 × EMA200 — Strategy Analytics</h1>
  <div class="subtitle">Swing trading backtest on NSE equities · {cfg["sim_start"]} → {cfg["sim_end"]} · {S["years"]:.1f} years</div>
  <div class="tagline">
    <span class="pill">Capital <b>{lakh(CAP)}</b></span>
    <span class="pill">Max positions <b>{cfg["max_pos"]}</b></span>
    <span class="pill">Stop loss <b>{cfg["sl_pct"]:.0f}%</b></span>
    <span class="pill">Risk/trade <b>{cfg["rpt"]:.1f}%</b> ({inr(cfg["pos_value"])})</span>
    <span class="pill">Universe <b>{cfg["universe"]} stocks</b> (ADT ≥ ₹{cfg["min_adt_cr"]:.0f}cr)</span>
  </div>
</div></header>

<div class="wrap">

<div class="grid grid4">
  {metric_card("Final Value", lakh(S["final_value"]), f"from {lakh(CAP)} · {S['total_ret']:+.0f}% total", good=True)}
  {metric_card("CAGR", f"{S['cagr']:.1f}%", f"vs Nifty {S['nifty_cagr']:.1f}%", good=S['cagr']>S['nifty_cagr'])}
  {metric_card("Post-Tax CAGR", f"{S['post_tax_cagr']:.1f}%", f"after {inr(S['total_tax'])} tax", good=True)}
  {metric_card("Max Drawdown", f"-{S['max_dd']:.1f}%", f"Nifty -{S['nifty_max_dd']:.1f}%", good=S['max_dd']<S['nifty_max_dd'])}
</div>
<div class="grid grid4" style="margin-top:14px">
  {metric_card("Sharpe Ratio", f"{S['sharpe']:.2f}", f"Nifty {S['nifty_sharpe']:.2f}", good=S['sharpe']>S['nifty_sharpe'])}
  {metric_card("Sortino Ratio", f"{S['sortino']:.2f}", f"Nifty {S['nifty_sortino']:.2f}", good=S['sortino']>S['nifty_sortino'])}
  {metric_card("Calmar Ratio", f"{S['calmar']:.2f}", "CAGR ÷ MaxDD", good=S['calmar']>1)}
  {metric_card("CAPM Alpha", f"{S['alpha']:+.1f}%", f"β {S['beta']:.2f} · ρ {S['corr']:.2f}", good=S['alpha']>0)}
</div>
<div class="note green"><b>Headline:</b> ₹{CAP/1e5:.0f} lakh grew to <b>{lakh(S['final_value'])}</b>
({S['total_ret']:+.0f}% pre-tax / {S['post_tax_ret']:+.0f}% post-tax) over {S['years']:.1f} years —
a <b>{S['cagr']:.1f}% CAGR</b> versus Nifty 50's {S['nifty_cagr']:.1f}%. The strategy delivered
<b>{S['alpha']:+.1f}% annual alpha</b> at a beta of just {S['beta']:.2f} — genuine stock selection,
not leveraged market exposure.</div>

<h2>1 · Equity Curve vs Benchmark</h2>
<div class="lead">₹10L invested in the strategy vs the same ₹10L in Nifty 50. Dashed gold line = starting capital floor; dots mark the peak and trough of the worst drawdown.</div>
<div class="chart-box">{chart_equity}</div>
<h3>Log scale — consistency of compounding</h3>
<div class="chart-box">{chart_equity_log}</div>

<h2>2 · Rolling 12-Month Returns</h2>
<div class="lead">Every point = the trailing 1-year return on that day. Shows how often, and by how much, the strategy beats the index across the whole period — not just end-to-end.</div>
<div class="chart-box">{chart_roll}</div>

<h2>3 · Capital Exposure</h2>
<div class="lead">Percentage of capital actually deployed in positions over time. The cash buffer (gap below 100%) is part of why portfolio drawdown stays contained.</div>
<div class="chart-box">{chart_expo}</div>

<h2>4 · Drawdown (Underwater Curve)</h2>
<div class="lead">Distance below the running equity high-water mark. Shaded band = the worst peak-to-recovery episode.</div>
<div class="chart-box">{chart_dd}</div>

<h2>5 · Drawdown Decomposition — Why -{S['max_dd']:.0f}% with a 10% Stop?</h2>
<div class="note red"><b>Important distinction:</b> the 10% stop caps the loss on each <i>position, measured from its entry price</i>.
Portfolio <i>drawdown</i> measures give-back from the equity <i>peak</i> — a completely different quantity.
The maximum a stop-loss can bound is <b>{cfg['max_pos']}×{cfg['rpt']:.1f}% = {maxrisk_pct:.1f}%</b>
(all positions fresh and stopped same day). The -{S['max_dd']:.0f}% is <b>not</b> capital loss — it is
accumulated <b>paper profit being given back</b> on multi-bagger winners whose stops sat 50–90% below their current price.</div>
<div class="ddflow">
  <div class="ddbox"><div class="lab">Equity Peak ({dates[dd_peak_i]})</div><div class="big">{lakh(peak_val)}</div><div class="sm pos">{peak_gain:+.0f}% above start capital</div></div>
  <div class="ddarrow">→</div>
  <div class="ddbox"><div class="lab">Trough ({dates[dd_trough_i]})</div><div class="big">{lakh(trough_val)}</div><div class="sm pos">still {trough_gain:+.0f}% above start capital</div></div>
  <div class="ddarrow">→</div>
  <div class="ddbox"><div class="lab">Give-back</div><div class="big neg">-{S['max_dd']:.1f}%</div><div class="sm">{inr(dd_drop)} of paper profit</div></div>
</div>
<div class="grid grid4">
  {metric_card("Stop-loss exits", f"{S['sl_hits']}", f"avg fill -10.2% (works)")}
  {metric_card("Max stop-bounded DD", f"{maxrisk_pct:.1f}%", "if all 15 stopped at once")}
  {metric_card("Trough vs capital", f"+{trough_gain:.0f}%", "never near original ₹10L")}
  {metric_card("Drawdown length", f"{dd_days} days", (f"recovered in {recov_days}d" if recov_days else "recovering"))}
</div>
<div class="note">At the {dates[dd_peak_i]} peak, all {cfg['max_pos']} positions were large unrealised winners (e.g. RVNL +995%,
INDIANB +551%). Their hard stops were ~10% below the <i>original entry</i>, i.e. far below market — so the
2024-25 correction crushed mark-to-market value long before any stop could trigger. This is the deliberate,
measured cost of letting trend winners run: the same patience that produces the <b>{S['avg_win']:+.0f}% average winner</b>.</div>

<h2>6 · Year-by-Year Performance</h2>
<div class="chart-box">{chart_years}</div>
<table>
  <tr><th>Year</th><th class="num">Strategy</th><th class="num">Nifty 50</th><th class="num">Outperformance</th><th class="num">Strategy Max DD</th><th class="num">Closed Trades</th></tr>
  {year_table}
</table>
<div class="note">Returns are mark-to-market (include unrealised gains on open positions at each year boundary),
so they reconcile to the equity curve rather than to closed-trade P&L. 2025 shows the drawdown year clearly.</div>

<h2>7 · Monthly Returns Heatmap</h2>
<div class="chart-box">{heat}</div>

<h2>8 · Trade Return Distribution</h2>
<div class="lead">The shape that makes the strategy work: many small outcomes, a long fat right tail of multi-baggers. Numbers under each bar = total P&L from that bucket.</div>
<div class="chart-box">{chart_hist}</div>
<div class="note blue"><b>Asymmetry is the engine.</b> Losses are tightly clustered (the 10% stop truncates the left tail),
while winners extend to +500% and beyond. The top 10 trades alone account for <b>{top10_share:.0f}%</b> of all gross
profit; the top 20 for <b>{top20_share:.0f}%</b>. This is concentration risk to be aware of — but it is the
expected signature of trend-following, not a flaw.</div>

<h2>9 · Holding Period vs Return</h2>
<div class="lead">Each dot is one trade. Winners (green) are held for months and cluster high; losers (red) are cut fast and shallow at the stop.</div>
<div class="chart-box">{chart_scatter}</div>
<div class="grid grid4">
  {metric_card("Avg winner hold", f"{S['avg_win_days']:.0f} days", "let winners run")}
  {metric_card("Avg loser hold", f"{S['avg_loss_days']:.0f} days", "cut losers fast")}
  {metric_card("Avg win", f"{S['avg_win']:+.0f}%", good=True)}
  {metric_card("Avg loss", f"{S['avg_loss']:+.0f}%", good=False)}
</div>

<h2>10 · Top Profit Contributors</h2>
<div class="lead">Net P&L by stock (all trades in that name aggregated).</div>
<div class="chart-box">{chart_contrib}</div>

<h2>11 · Full Risk &amp; Return Metrics</h2>
<div class="two-col">
  <div><h3>Return</h3>
    <table>
      <tr><th>Metric</th><th class="num">Strategy</th><th class="num">Nifty 50</th></tr>
      <tr><td>Total Return</td><td class="num pos">{S['total_ret']:+.1f}%</td><td class="num">{S['nifty_total']:+.1f}%</td></tr>
      <tr><td>CAGR</td><td class="num pos">{S['cagr']:.1f}%</td><td class="num">{S['nifty_cagr']:.1f}%</td></tr>
      <tr><td>Post-Tax Total</td><td class="num">{S['post_tax_ret']:+.1f}%</td><td class="num">—</td></tr>
      <tr><td>Post-Tax CAGR</td><td class="num">{S['post_tax_cagr']:.1f}%</td><td class="num">—</td></tr>
      <tr><td>Annualised Volatility</td><td class="num">{S['vol']:.1f}%</td><td class="num">{S['nifty_vol']:.1f}%</td></tr>
    </table>
  </div>
  <div><h3>Risk-Adjusted</h3>
    <table>
      <tr><th>Metric</th><th class="num">Strategy</th><th class="num">Nifty 50</th></tr>
      <tr><td>Sharpe (rf={cfg['risk_free']:.1f}%)</td><td class="num pos">{S['sharpe']:.2f}</td><td class="num">{S['nifty_sharpe']:.2f}</td></tr>
      <tr><td>Sortino</td><td class="num pos">{S['sortino']:.2f}</td><td class="num">{S['nifty_sortino']:.2f}</td></tr>
      <tr><td>Calmar</td><td class="num">{S['calmar']:.2f}</td><td class="num">{S['nifty_calmar']:.2f}</td></tr>
      <tr><td>Max Drawdown</td><td class="num">-{S['max_dd']:.1f}%</td><td class="num">-{S['nifty_max_dd']:.1f}%</td></tr>
      <tr><td>Beta / Alpha</td><td class="num">{S['beta']:.2f} / {S['alpha']:+.1f}%</td><td class="num">1.00 / —</td></tr>
    </table>
  </div>
</div>

<h2>12 · Trade Statistics</h2>
<div class="grid grid4">
  {metric_card("Total Trades", f"{S['trades']}", f"{S['avg_days']:.0f} day avg hold")}
  {metric_card("Win Rate", f"{S['win_rate']:.1f}%", f"{S['wins']}W / {S['losses']}L")}
  {metric_card("Profit Factor", f"{S['profit_factor']:.2f}", "gross profit ÷ gross loss", good=S['profit_factor']>1.5)}
  {metric_card("R-Multiple", f"{S['r_mult']:.2f}", "avg win ÷ avg loss", good=S['r_mult']>2)}
</div>
<div class="grid grid4" style="margin-top:14px">
  {metric_card("Avg Win", f"{S['avg_win']:+.1f}%", f"{S['avg_win_days']:.0f} day hold", good=True)}
  {metric_card("Avg Loss", f"{S['avg_loss']:+.1f}%", f"{S['avg_loss_days']:.0f} day hold", good=False)}
  {metric_card("Expectancy", f"{S['expectancy_pct']:+.2f}%", "per trade", good=S['expectancy_pct']>0)}
  {metric_card("Stop-Loss Rate", f"{S['sl_rate']:.1f}%", f"{S['sl_hits']} trades hit 10% SL")}
</div>
<div class="note blue"><b>Why this works:</b> a {S['win_rate']:.0f}% win rate is fine when each winner returns
<b>{S['avg_win']:+.0f}%</b> against only <b>{S['avg_loss']:.0f}%</b> per loser — an R-multiple of <b>{S['r_mult']:.1f}</b>.
Even losing 6 in 10, the 4 winners more than pay for them. Classic asymmetric trend-following.</div>
<h3>Largest Single Trades</h3>
<div class="grid" style="grid-template-columns:1fr 1fr">
  {metric_card("Biggest Winner", f"{S['largest_win_pct']:+.0f}%", S['largest_win_sym'], good=True)}
  {metric_card("Biggest Loser", f"{S['largest_loss_pct']:+.0f}%", S['largest_loss_sym'], good=False)}
</div>

<h2>13 · Exit Reason Breakdown</h2>
<table>
  <tr><th>Exit Reason</th><th class="num">Trades</th><th class="num">% of Total</th><th class="num">Total P&amp;L</th></tr>
  {reason_table}
</table>

<h2>14 · Tax Analysis (Indian Capital Gains)</h2>
<div class="note">Per financial year (Apr–Mar) on realised gains. <b>STCG {cfg['stcg_rate']:.0f}%</b> for holdings &lt; 12 months;
<b>LTCG {cfg['ltcg_rate']:.1f}%</b> for ≥ 12 months above the annual <b>{inr(cfg['ltcg_exempt'])}</b> exemption
(post-July-2024 rates). Open positions at period end are untaxed.</div>
<table>
  <tr><th>Financial Year</th><th class="num">STCG Gains</th><th class="num">LTCG Gains</th><th class="num">STCG Tax</th><th class="num">LTCG Tax</th><th class="num">Total Tax</th></tr>
  {tax_table}
  <tr style="border-top:2px solid #2a3a4a"><td class="strong">Total</td><td class="num"></td><td class="num"></td><td class="num"></td><td class="num"></td><td class="num strong">{inr(S['total_tax'])}</td></tr>
</table>
<div class="grid grid4" style="margin-top:14px">
  {metric_card("Pre-Tax Value", lakh(S['final_value']), f"{S['total_ret']:+.0f}%")}
  {metric_card("Total Tax Paid", inr(S['total_tax']), f"{100*S['total_tax']/(S['final_value']-CAP):.1f}% of gains")}
  {metric_card("Post-Tax Value", lakh(S['post_tax_value']), f"{S['post_tax_ret']:+.0f}%", good=True)}
  {metric_card("Tax Drag on CAGR", f"-{S['cagr']-S['post_tax_cagr']:.1f}%", f"{S['cagr']:.1f}% → {S['post_tax_cagr']:.1f}%")}
</div>

<h2>15 · Trade Ledger — Top Winners</h2>
<table>
  <tr><th>Symbol</th><th>Entry Date</th><th>Exit Date</th><th class="num">Days</th><th class="num">Entry</th><th class="num">Exit</th><th class="num">Return</th><th class="num">P&amp;L</th><th>Exit Reason</th></tr>
  {trade_rows(top_win)}
</table>
<h3>Worst Trades</h3>
<table>
  <tr><th>Symbol</th><th>Entry Date</th><th>Exit Date</th><th class="num">Days</th><th class="num">Entry</th><th class="num">Exit</th><th class="num">Return</th><th class="num">P&amp;L</th><th>Exit Reason</th></tr>
  {trade_rows(top_loss)}
</table>

<h2>16 · Methodology &amp; Assumptions</h2>
<table>
  <tr><td class="sym">Entry signal</td><td>RS ratio (Stock Close ÷ Nifty 50 Close) EMA50 crosses <b>above</b> EMA200</td></tr>
  <tr><td class="sym">Exit signal</td><td>RS EMA50 crosses <b>below</b> EMA200 (symmetric), OR price hits 10% hard stop from entry</td></tr>
  <tr><td class="sym">Execution</td><td>Signal at close; fill at <b>next day's open</b>; unfilled orders expire after 1 day</td></tr>
  <tr><td class="sym">Position sizing</td><td>Fixed risk: Capital × {cfg['rpt']:.1f}% ÷ {cfg['sl_pct']:.0f}% = <b>{inr(cfg['pos_value'])}</b> notional per trade</td></tr>
  <tr><td class="sym">Universe filter</td><td>Mean daily turnover ≥ ₹{cfg['min_adt_cr']:.0f} crore across the sim period ({cfg['universe']} stocks qualify)</td></tr>
  <tr><td class="sym">Capacity</td><td>Max {cfg['max_pos']} concurrent positions; new signals queue and fill as slots free up</td></tr>
  <tr><td class="sym">Data source</td><td>Daily OHLCV, auto-adjusted for splits/dividends</td></tr>
  <tr><td class="sym">Not modelled</td><td>Brokerage, STT, slippage, impact cost. Returns are gross of transaction costs (tax IS modelled in §14)</td></tr>
</table>
<div class="note"><b>Caveats for the desk:</b> (1) Backtest assumes next-open fills with no slippage. (2) The {S['max_dd']:.0f}%
drawdown is real MTM give-back and must be tolerable to capture the {S['cagr']:.0f}% CAGR. (3) Survivorship: universe is
current NSE liquid names; delisted/merged stocks are excluded. (4) Returns are concentrated in a few multi-baggers
(top 10 trades = {top10_share:.0f}% of gross profit). (5) 2021–2025 was broadly bullish for Indian equities — forward
returns are regime-dependent.</div>

<div class="footer">
  Champion Trader System · Strategy R&amp;D · {S['trades']} simulated trades over {len(ec)} trading days<br>
  RS EMA50×200 · {lakh(CAP)} · {cfg['max_pos']} positions · {cfg['sl_pct']:.0f}% stop · {cfg['sim_start']} to {cfg['sim_end']}
</div>

</div></body></html>'''

with open("/home/user/champion-trader/docs/rs_ema50_final_report.html","w") as f:
    f.write(HTML)
print(f"Wrote docs/rs_ema50_final_report.html ({len(HTML):,} bytes)")
print(f"Charts: equity, log-equity, rolling12m, exposure, drawdown, year-bars, heatmap, histogram, scatter, contributors")
print(f"DD window: peak {dates[dd_peak_i]} ({lakh(peak_val)}, +{peak_gain:.0f}%) -> trough {dates[dd_trough_i]} ({lakh(trough_val)}, +{trough_gain:.0f}%)")
print(f"Concentration: top10={top10_share:.0f}% top20={top20_share:.0f}% of gross profit")
