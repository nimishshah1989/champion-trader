"""
Generate self-contained HTML analytics report from /tmp/final_sim_bundle.pkl
All charts are inline SVG → no external dependencies, emailable to a fund manager.
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

def inr(x, dec=0):
    """Indian comma formatting."""
    neg = x < 0; x = abs(x)
    s = f"{x:.{dec}f}"
    if "." in s: intp, decp = s.split("."); decp="."+decp
    else: intp, decp = s, ""
    if len(intp) > 3:
        last3 = intp[-3:]; rest = intp[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:]); rest = rest[:-2]
        if rest: parts.insert(0, rest)
        intp = ",".join(parts) + "," + last3
    return ("-" if neg else "") + "₹" + intp + decp

def lakh(x):
    """Express in lakhs."""
    return f"₹{x/1e5:.2f}L"

# ─── SVG line chart helper ───────────────────────────────────────────────────
def svg_dual_line(series_a, series_b, labels, colors, width=1080, height=420,
                  pad=60, title="", y_is_currency=True, logscale=False):
    """series_a/b: list of (x_index, value). Both share x axis 0..n-1."""
    n = len(series_a)
    ax = [v for _,v in series_a]
    bx = [v for _,v in series_b] if series_b else []
    allv = ax + bx
    ymin, ymax = min(allv), max(allv)
    if logscale:
        import math
        ymin_l, ymax_l = math.log10(max(ymin,1)), math.log10(ymax)
        def yv(v): return math.log10(max(v,1))
    else:
        def yv(v): return v
        ymin_l, ymax_l = ymin, ymax
    yr = ymax_l - ymin_l or 1
    def X(i): return pad + i*(width-2*pad)/(n-1)
    def Y(v): return height-pad - (yv(v)-ymin_l)/yr*(height-2*pad)
    def path(series):
        pts = [f"{X(i):.1f},{Y(v):.1f}" for i,(_,v) in enumerate(series)]
        return "M" + " L".join(pts)
    # gridlines (5)
    grid=""; lbls=""
    for g in range(6):
        gy = height-pad - g*(height-2*pad)/5
        val = ymin_l + g*yr/5
        rv = (10**val) if logscale else val
        grid += f'<line x1="{pad}" y1="{gy:.1f}" x2="{width-pad}" y2="{gy:.1f}" stroke="#1e2a38" stroke-width="1"/>'
        lab = lakh(rv) if y_is_currency else f"{rv:.0f}"
        lbls += f'<text x="{pad-8}" y="{gy+4:.1f}" fill="#5b6b7d" font-size="11" text-anchor="end">{lab}</text>'
    # x labels (year boundaries)
    xlbls=""; seen=set()
    for i,(d,_) in enumerate(series_a):
        ylab = d[:4]
        if ylab not in seen:
            seen.add(ylab)
            xlbls += f'<line x1="{X(i):.1f}" y1="{pad}" x2="{X(i):.1f}" y2="{height-pad}" stroke="#16202b" stroke-width="1"/>'
            xlbls += f'<text x="{X(i):.1f}" y="{height-pad+18}" fill="#5b6b7d" font-size="11" text-anchor="middle">{ylab}</text>'
    fill_a = ""
    # area under a
    area_pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i,(_,v) in enumerate(series_a))
    fill_a = f'<polygon points="{X(0):.1f},{height-pad:.1f} {area_pts} {X(n-1):.1f},{height-pad:.1f}" fill="{colors[0]}" opacity="0.08"/>'
    pa = f'<path d="{path(series_a)}" fill="none" stroke="{colors[0]}" stroke-width="2.2"/>'
    pb = f'<path d="{path(series_b)}" fill="none" stroke="{colors[1]}" stroke-width="1.8" opacity="0.85"/>' if series_b else ""
    # legend
    leg = f'''<g font-size="13">
      <rect x="{pad+8}" y="{pad+6}" width="13" height="13" fill="{colors[0]}"/>
      <text x="{pad+28}" y="{pad+17}" fill="#c9d6e3">{labels[0]}</text>'''
    if series_b:
        leg += f'''<rect x="{pad+8}" y="{pad+26}" width="13" height="13" fill="{colors[1]}"/>
      <text x="{pad+28}" y="{pad+37}" fill="#c9d6e3">{labels[1]}</text>'''
    leg += "</g>"
    return f'''<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">
      {grid}{xlbls}{lbls}{fill_a}{pb}{pa}{leg}</svg>'''

def svg_area_dd(series, width=1080, height=260, pad=60, color="#e05260"):
    n=len(series); vals=[v for _,v in series]
    ymax = max(vals) or 1
    def X(i): return pad + i*(width-2*pad)/(n-1)
    def Y(v): return pad + (v/ymax)*(height-2*pad)   # inverted: 0 at top
    grid=""; lbls=""
    for g in range(5):
        val = g*ymax/4
        gy = pad + (val/ymax)*(height-2*pad)
        grid += f'<line x1="{pad}" y1="{gy:.1f}" x2="{width-pad}" y2="{gy:.1f}" stroke="#1e2a38" stroke-width="1"/>'
        lbls += f'<text x="{pad-8}" y="{gy+4:.1f}" fill="#5b6b7d" font-size="11" text-anchor="end">-{val:.0f}%</text>'
    xlbls=""; seen=set()
    for i,(d,_) in enumerate(series):
        yr=d[:4]
        if yr not in seen:
            seen.add(yr)
            xlbls += f'<text x="{X(i):.1f}" y="{height-pad+18}" fill="#5b6b7d" font-size="11" text-anchor="middle">{yr}</text>'
    pts=" ".join(f"{X(i):.1f},{Y(v):.1f}" for i,(_,v) in enumerate(series))
    poly=f'<polygon points="{X(0):.1f},{pad:.1f} {pts} {X(n-1):.1f},{pad:.1f}" fill="{color}" opacity="0.25"/>'
    line=f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8"/>'
    return f'''<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">
      {grid}{xlbls}{lbls}{poly}{line}</svg>'''

def svg_bar_years(rows, width=1080, height=340, pad=60):
    """rows: (year, strat_ret, nifty_ret, dd, ntrades). Grouped bars."""
    n=len(rows)
    vals=[r[1] for r in rows]+[r[2] for r in rows]
    ymax=max(vals+[5]); ymin=min(vals+[0])
    span=ymax-ymin or 1
    gw=(width-2*pad)/n
    def Y(v): return height-pad - (v-ymin)/span*(height-2*pad)
    zero=Y(0)
    bars=""; xlbls=""
    bw=gw*0.32
    for i,r in enumerate(rows):
        cx=pad+i*gw+gw/2
        s_y=Y(r[1]); n_y=Y(r[2])
        # strat bar
        sy0=min(s_y,zero); sh=abs(s_y-zero)
        col_s = "#3fb950" if r[1]>=0 else "#e05260"
        bars+=f'<rect x="{cx-bw-2:.1f}" y="{sy0:.1f}" width="{bw:.1f}" height="{sh:.1f}" fill="{col_s}"/>'
        bars+=f'<text x="{cx-bw/2-2:.1f}" y="{sy0-4 if r[1]>=0 else sy0+sh+12:.1f}" fill="#c9d6e3" font-size="10" text-anchor="middle">{r[1]:+.0f}</text>'
        # nifty bar
        ny0=min(n_y,zero); nh=abs(n_y-zero)
        bars+=f'<rect x="{cx+2:.1f}" y="{ny0:.1f}" width="{bw:.1f}" height="{nh:.1f}" fill="#4a7dbf" opacity="0.8"/>'
        bars+=f'<text x="{cx+bw/2+2:.1f}" y="{ny0-4 if r[2]>=0 else ny0+nh+12:.1f}" fill="#7e93a8" font-size="10" text-anchor="middle">{r[2]:+.0f}</text>'
        xlbls+=f'<text x="{cx:.1f}" y="{height-pad+18}" fill="#8a9bad" font-size="12" text-anchor="middle">{r[0]}</text>'
    axis=f'<line x1="{pad}" y1="{zero:.1f}" x2="{width-pad}" y2="{zero:.1f}" stroke="#3a4a5a" stroke-width="1.5"/>'
    leg=f'''<g font-size="13"><rect x="{pad+8}" y="14" width="13" height="13" fill="#3fb950"/>
      <text x="{pad+28}" y="25" fill="#c9d6e3">Strategy</text>
      <rect x="{pad+120}" y="14" width="13" height="13" fill="#4a7dbf"/>
      <text x="{pad+140}" y="25" fill="#c9d6e3">Nifty 50</text></g>'''
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{axis}{bars}{xlbls}{leg}</svg>'

# Build normalized equity vs benchmark (both start at CAPITAL)
eq_series = [(d, v) for d,v,_,_,_ in ec]
n0 = nc[0][1]
bench_series = [(d, CAP*(v/n0)) for d,v in nc]

# Exposure series (invested / port)
expo_series = [(d, 100*inv/v if v>0 else 0) for d,v,cash,inv,np_ in ec]

chart_equity = svg_dual_line(eq_series, bench_series,
    ["RS EMA50×200 Strategy","Nifty 50 (buy & hold)"], ["#3fb950","#4a7dbf"],
    y_is_currency=True)
chart_equity_log = svg_dual_line(eq_series, bench_series,
    ["RS EMA50×200 Strategy (log)","Nifty 50 (log)"], ["#3fb950","#4a7dbf"],
    y_is_currency=True, logscale=True)
chart_dd = svg_area_dd(dds)
chart_years = svg_bar_years(year_rows)

# Monthly heatmap
mk = sorted(month_ret.keys())
years_m = sorted(set(int(k[:4]) for k in mk))
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
def heat_color(v):
    if v is None: return "#0d1620"
    if v>=0:
        a=min(v/12,1); return f"rgba(63,185,80,{0.15+0.7*a:.2f})"
    else:
        a=min(-v/12,1); return f"rgba(224,82,96,{0.15+0.7*a:.2f})"
heat="<table class='heat'><tr><th></th>"+"".join(f"<th>{m}</th>" for m in months)+"<th>Year</th></tr>"
for y in years_m:
    heat+=f"<tr><td class='yr'>{y}</td>"
    yr_compound=1.0
    for mi in range(12):
        key=f"{y}-{mi+1:02d}"
        v=month_ret.get(key)
        if v is not None: yr_compound*=(1+v/100)
        cell="" if v is None else f"{v:+.1f}"
        heat+=f"<td style='background:{heat_color(v)}'>{cell}</td>"
    yc=(yr_compound-1)*100 if yr_compound!=1.0 else None
    heat+=f"<td class='yr' style='background:{heat_color(yc)}'>{'' if yc is None else f'{yc:+.1f}'}</td></tr>"
heat+="</table>"

# Trade ledger (top winners + top losers + recent)
trades_sorted = sorted(trades, key=lambda t:t["pnl_pct"], reverse=True)
top_win = trades_sorted[:12]
top_loss = trades_sorted[-8:]
def trade_rows(ts):
    r=""
    for t in ts:
        cls="pos" if t["pnl"]>0 else "neg"
        rcls={"Stop loss":"badge-sl","RS reversal":"badge-rs","Open at end":"badge-open"}.get(t["reason"],"")
        r+=f'''<tr>
          <td class="sym">{html.escape(t["sym"])}</td>
          <td>{t["entry_date"]}</td><td>{t["exit_date"]}</td>
          <td class="num">{t["days"]}</td>
          <td class="num">₹{t["entry"]:.1f}</td><td class="num">₹{t["exit"]:.1f}</td>
          <td class="num {cls}">{t["pnl_pct"]:+.1f}%</td>
          <td class="num {cls}">{inr(t["pnl"])}</td>
          <td><span class="badge {rcls}">{t["reason"]}</span></td></tr>'''
    return r

# Exit reason breakdown
from collections import Counter
reason_ct = Counter(t["reason"] for t in trades)
reason_pnl = {}
for t in trades:
    reason_pnl.setdefault(t["reason"],0)
    reason_pnl[t["reason"]]+=t["pnl"]

def metric_card(label, value, sub="", good=None):
    cls=""
    if good is True: cls="pos"
    elif good is False: cls="neg"
    return f'''<div class="card">
      <div class="card-label">{label}</div>
      <div class="card-value {cls}">{value}</div>
      <div class="card-sub">{sub}</div></div>'''

# ─── Assemble HTML ───────────────────────────────────────────────────────────
tax_table=""
for fy,stcg,ltcg,st_tax,lt_tax,tot in tax_rows:
    tax_table+=f'''<tr><td>{fy}</td>
      <td class="num">{inr(stcg)}</td><td class="num">{inr(ltcg)}</td>
      <td class="num">{inr(st_tax)}</td><td class="num">{inr(lt_tax)}</td>
      <td class="num strong">{inr(tot)}</td></tr>'''

year_table=""
for yr,sr,nr,dd,ntr in year_rows:
    out_cls="pos" if sr>nr else "neg"
    year_table+=f'''<tr><td>{yr}</td>
      <td class="num {'pos' if sr>=0 else 'neg'}">{sr:+.1f}%</td>
      <td class="num {'pos' if nr>=0 else 'neg'}">{nr:+.1f}%</td>
      <td class="num {out_cls}">{sr-nr:+.1f}%</td>
      <td class="num">{dd:.1f}%</td>
      <td class="num">{ntr}</td></tr>'''

reason_table=""
for rsn,ct in reason_ct.most_common():
    pnl=reason_pnl[rsn]
    reason_table+=f'''<tr><td>{rsn}</td><td class="num">{ct}</td>
      <td class="num">{100*ct/len(trades):.1f}%</td>
      <td class="num {'pos' if pnl>=0 else 'neg'}">{inr(pnl)}</td></tr>'''

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
  h2{{font-size:21px;color:#fff;margin:42px 0 18px;padding-bottom:10px;border-bottom:1px solid #1c2c3c;font-weight:650}}
  h3{{font-size:15px;color:#9fb2c4;margin:24px 0 12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px}}
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
  .note.green{{border-left-color:#3fb950}}
  .note.blue{{border-left-color:#4a7dbf}}
  .footer{{margin-top:50px;padding-top:24px;border-top:1px solid #1c2c3c;color:#5b6b7d;font-size:12px;text-align:center}}
  .winner{{background:linear-gradient(135deg,#0f2418 0%,#102a1c 100%);border:1px solid #1e4a30}}
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

<!-- HEADLINE METRICS -->
<div class="grid grid4">
  {metric_card("Final Value", lakh(S["final_value"]), f"from {lakh(CAP)} · {S['total_ret']:+.0f}% total", good=True)}
  {metric_card("CAGR", f"{S['cagr']:.1f}%", f"vs Nifty {S['nifty_cagr']:.1f}%", good=S['cagr']>S['nifty_cagr'])}
  {metric_card("Post-Tax CAGR", f"{S['post_tax_cagr']:.1f}%", f"after {inr(S['total_tax'])} tax", good=True)}
  {metric_card("Max Drawdown", f"-{S['max_dd']:.1f}%", f"Nifty -{S['nifty_max_dd']:.1f}%", good=S['max_dd']<S['nifty_max_dd'])}
</div>
<div class="grid grid4" style="margin-top:14px">
  {metric_card("Sharpe Ratio", f"{S['sharpe']:.2f}", f"Nifty {S['nifty_sharpe']:.2f}", good=S['sharpe']>S['nifty_sharpe'])}
  {metric_card("Sortino Ratio", f"{S['sortino']:.2f}", f"Nifty {S['nifty_sortino']:.2f}", good=S['sortino']>S['nifty_sortino'])}
  {metric_card("Calmar Ratio", f"{S['calmar']:.2f}", f"CAGR ÷ MaxDD", good=S['calmar']>1)}
  {metric_card("CAPM Alpha", f"{S['alpha']:+.1f}%", f"β {S['beta']:.2f} · ρ {S['corr']:.2f}", good=S['alpha']>0)}
</div>

<div class="note green"><b>Headline:</b> ₹{CAP/1e5:.0f} lakh grew to <b>{lakh(S['final_value'])}</b>
({S['total_ret']:+.0f}% pre-tax / {S['post_tax_ret']:+.0f}% post-tax) over {S['years']:.1f} years —
a <b>{S['cagr']:.1f}% CAGR</b> versus Nifty 50's {S['nifty_cagr']:.1f}%. The strategy delivered
<b>{S['alpha']:+.1f}% annual alpha</b> at a beta of just {S['beta']:.2f}, meaning the outperformance is
genuine stock selection — not leveraged market exposure.</div>

<!-- EQUITY CURVE -->
<h2>Equity Curve vs Benchmark</h2>
<div class="chart-box">{chart_equity}</div>
<h3>Log scale (to judge consistency of compounding)</h3>
<div class="chart-box">{chart_equity_log}</div>

<!-- DRAWDOWN -->
<h2>Drawdown (Underwater Curve)</h2>
<div class="chart-box">{chart_dd}</div>
<div class="note">Maximum drawdown of <b>-{S['max_dd']:.1f}%</b>, with the longest peak-to-recovery
stretch lasting <b>{S['longest_dd_days']} trading days</b> (~{S['longest_dd_days']/21:.0f} months).
This is the price of holding trend winners through consolidations — the same patience that produced the
<b>{S['avg_win']:+.0f}% average winning trade</b>.</div>

<!-- YEAR-WISE -->
<h2>Year-by-Year Performance</h2>
<div class="chart-box">{chart_years}</div>
<table>
  <tr><th>Year</th><th class="num">Strategy</th><th class="num">Nifty 50</th>
      <th class="num">Outperformance</th><th class="num">Strategy Max DD</th><th class="num">Closed Trades</th></tr>
  {year_table}
</table>
<div class="note">Returns are mark-to-market (include unrealised gains on open positions at each year boundary),
which is why they reconcile to the equity curve rather than to closed-trade P&L. Trend-following winners
routinely span calendar years.</div>

<!-- MONTHLY HEATMAP -->
<h2>Monthly Returns Heatmap</h2>
<div class="chart-box">{heat}</div>

<!-- RETURN & RISK METRICS -->
<h2>Full Risk & Return Metrics</h2>
<div class="two-col">
  <div>
    <h3>Return</h3>
    <table>
      <tr><th>Metric</th><th class="num">Strategy</th><th class="num">Nifty 50</th></tr>
      <tr><td>Total Return</td><td class="num pos">{S['total_ret']:+.1f}%</td><td class="num">{S['nifty_total']:+.1f}%</td></tr>
      <tr><td>CAGR</td><td class="num pos">{S['cagr']:.1f}%</td><td class="num">{S['nifty_cagr']:.1f}%</td></tr>
      <tr><td>Post-Tax Total</td><td class="num">{S['post_tax_ret']:+.1f}%</td><td class="num">—</td></tr>
      <tr><td>Post-Tax CAGR</td><td class="num">{S['post_tax_cagr']:.1f}%</td><td class="num">—</td></tr>
      <tr><td>Annualised Volatility</td><td class="num">{S['vol']:.1f}%</td><td class="num">{S['nifty_vol']:.1f}%</td></tr>
    </table>
  </div>
  <div>
    <h3>Risk-Adjusted</h3>
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

<!-- TRADE STATS -->
<h2>Trade Statistics</h2>
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
<div class="note blue"><b>Why this works:</b> A {S['win_rate']:.0f}% win rate sounds modest, but each winner
returns <b>{S['avg_win']:+.0f}%</b> against only <b>{S['avg_loss']:.0f}%</b> per loser — an R-multiple of
<b>{S['r_mult']:.1f}</b>. The math: even losing 6 in 10 trades, the 4 winners more than pay for them. This is a
classic <b>asymmetric trend-following</b> profile — cut losers fast at the 10% stop, let winners run for months.</div>

<h3>Largest Single Trade</h3>
<div class="grid" style="grid-template-columns:1fr 1fr">
  {metric_card("Biggest Winner", f"{S['largest_win_pct']:+.0f}%", S['largest_win_sym'], good=True)}
  {metric_card("Biggest Loser", f"{S['largest_loss_pct']:+.0f}%", S['largest_loss_sym'], good=False)}
</div>

<!-- EXIT BREAKDOWN -->
<h2>Exit Reason Breakdown</h2>
<table>
  <tr><th>Exit Reason</th><th class="num">Trades</th><th class="num">% of Total</th><th class="num">Total P&amp;L</th></tr>
  {reason_table}
</table>

<!-- TAX -->
<h2>Tax Analysis (Indian Capital Gains)</h2>
<div class="note">Computed per financial year (Apr–Mar) on realised gains only. <b>STCG {cfg['stcg_rate']:.0f}%</b>
for holdings &lt; 12 months; <b>LTCG {cfg['ltcg_rate']:.1f}%</b> for holdings ≥ 12 months above the annual
<b>{inr(cfg['ltcg_exempt'])}</b> exemption (post-July-2024 rates). Open positions at period end are untaxed.</div>
<table>
  <tr><th>Financial Year</th><th class="num">STCG Gains</th><th class="num">LTCG Gains</th>
      <th class="num">STCG Tax</th><th class="num">LTCG Tax</th><th class="num">Total Tax</th></tr>
  {tax_table}
  <tr style="border-top:2px solid #2a3a4a"><td class="strong">Total</td>
    <td class="num"></td><td class="num"></td><td class="num"></td><td class="num"></td>
    <td class="num strong">{inr(S['total_tax'])}</td></tr>
</table>
<div class="grid grid4" style="margin-top:14px">
  {metric_card("Pre-Tax Value", lakh(S['final_value']), f"{S['total_ret']:+.0f}%")}
  {metric_card("Total Tax Paid", inr(S['total_tax']), f"{100*S['total_tax']/(S['final_value']-CAP):.1f}% of gains")}
  {metric_card("Post-Tax Value", lakh(S['post_tax_value']), f"{S['post_tax_ret']:+.0f}%", good=True)}
  {metric_card("Tax Drag on CAGR", f"-{S['cagr']-S['post_tax_cagr']:.1f}%", f"{S['cagr']:.1f}% → {S['post_tax_cagr']:.1f}%")}
</div>

<!-- TRADE LEDGER -->
<h2>Trade Ledger — Top Winners</h2>
<table>
  <tr><th>Symbol</th><th>Entry Date</th><th>Exit Date</th><th class="num">Days</th>
      <th class="num">Entry</th><th class="num">Exit</th><th class="num">Return</th>
      <th class="num">P&amp;L</th><th>Exit Reason</th></tr>
  {trade_rows(top_win)}
</table>
<h3>Worst Trades</h3>
<table>
  <tr><th>Symbol</th><th>Entry Date</th><th>Exit Date</th><th class="num">Days</th>
      <th class="num">Entry</th><th class="num">Exit</th><th class="num">Return</th>
      <th class="num">P&amp;L</th><th>Exit Reason</th></tr>
  {trade_rows(top_loss)}
</table>

<!-- METHODOLOGY -->
<h2>Methodology &amp; Assumptions</h2>
<table>
  <tr><td class="sym">Entry signal</td><td>RS ratio (Stock Close ÷ Nifty 50 Close) EMA50 crosses <b>above</b> EMA200</td></tr>
  <tr><td class="sym">Exit signal</td><td>RS EMA50 crosses <b>below</b> EMA200 (symmetric), OR price hits 10% hard stop from entry</td></tr>
  <tr><td class="sym">Execution</td><td>Signal computed at day's close; order filled at <b>next day's open</b>; unfilled orders expire after 1 day</td></tr>
  <tr><td class="sym">Position sizing</td><td>Fixed risk: Capital × {cfg['rpt']:.1f}% ÷ {cfg['sl_pct']:.0f}% = <b>{inr(cfg['pos_value'])}</b> notional per trade</td></tr>
  <tr><td class="sym">Universe filter</td><td>Mean daily turnover ≥ ₹{cfg['min_adt_cr']:.0f} crore across the sim period ({cfg['universe']} stocks qualify)</td></tr>
  <tr><td class="sym">Capacity</td><td>Maximum {cfg['max_pos']} concurrent positions; new signals queue and fill as slots free up</td></tr>
  <tr><td class="sym">Data source</td><td>Daily OHLCV, auto-adjusted for splits/dividends</td></tr>
  <tr><td class="sym">Not modelled</td><td>Brokerage, STT, slippage, impact cost. Returns are gross of transaction costs (tax IS modelled separately above)</td></tr>
</table>
<div class="note"><b>Caveats for the desk:</b> (1) Backtest assumes perfect next-open fills with no slippage —
real fills on 15 concurrent swing positions will incur some cost. (2) The {S['max_dd']:.0f}% drawdown is real and
must be tolerable to capture the {S['cagr']:.0f}% CAGR. (3) Survivorship: universe is current NSE liquid names;
delisted/merged stocks are not included. (4) 2021–2025 was a broadly bullish regime for Indian equities —
forward returns depend on regime.</div>

<div class="footer">
  Champion Trader System · Strategy R&amp;D · Generated from {S['trades']} simulated trades over {len(ec)} trading days<br>
  RS EMA50×200 · {lakh(CAP)} · {cfg['max_pos']} positions · {cfg['sl_pct']:.0f}% stop · {cfg['sim_start']} to {cfg['sim_end']}
</div>

</div></body></html>'''

with open("/home/user/champion-trader/docs/rs_ema50_final_report.html","w") as f:
    f.write(HTML)
print(f"Wrote docs/rs_ema50_final_report.html ({len(HTML):,} bytes)")
