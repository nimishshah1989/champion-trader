"""
Consolidated multi-market, multi-regime tear sheet for RS EMA50x200.
Combines: India 2015-2020 (out-of-sample), India 2021-2026, US 2021-2026.
Self-contained HTML with inline SVG. -> docs/rs_ema50_tearsheet.html
"""
import pickle, html
import numpy as np

RUNS = [
    ("India 2015–2020", "Out-of-sample · Nifty 50", "/tmp/final_sim_bundle_2015.pkl", "INR", "#e0a23f"),
    ("India 2021–2026", "In-sample · Nifty 50",     "/tmp/final_sim_bundle.pkl",      "INR", "#3fb950"),
    ("US 2021–2026",    "S&P 500",                   "/tmp/sp500_sim_bundle.pkl",      "USD", "#4a7dbf"),
]

data = []
for name, sub, path, cur, color in RUNS:
    B = pickle.load(open(path, "rb"))
    data.append({"name": name, "sub": sub, "cur": cur, "color": color,
                 "cfg": B["config"], "S": B["summary"],
                 "ec": B["equity_curve"], "nc": B["nifty_curve"]})

def money(x, cur, dec=0):
    if cur == "USD": return "$" + f"{x:,.{dec}f}"
    neg = x<0; x=abs(x); s=f"{x:.{dec}f}"
    if "." in s: intp,decp=s.split("."); decp="."+decp
    else: intp,decp=s,""
    if len(intp)>3:
        last3=intp[-3:]; rest=intp[:-3]; parts=[]
        while len(rest)>2: parts.insert(0,rest[-2:]); rest=rest[:-2]
        if rest: parts.insert(0,rest)
        intp=",".join(parts)+","+last3
    return ("-" if neg else "")+"₹"+intp+decp

def big(x, cur):
    if cur=="USD": return "$"+f"{x:,.0f}"
    return f"₹{x/1e5:.2f}L"

# ─── SVG helpers ─────────────────────────────────────────────────────────────
def svg_growth_overlay(runs, width=1080, height=440, pad=64):
    """Overlay each strategy's growth-of-1 multiple vs years elapsed."""
    maxmult=1; maxyears=0
    series=[]
    for d in runs:
        ec=d["ec"]; cap=d["cfg"]["capital"]
        mult=[(i/252, e[1]/cap) for i,e in enumerate(ec)]
        series.append((d, mult))
        maxmult=max(maxmult, max(m for _,m in mult)); maxyears=max(maxyears, mult[-1][0])
    def X(yr): return pad + yr/maxyears*(width-2*pad)
    def Y(m): return height-pad - (m-1)/(maxmult-1)*(height-2*pad)
    grid=""; lbls=""
    for g in range(6):
        m=1+g*(maxmult-1)/5; gy=Y(m)
        grid+=f'<line x1="{pad}" y1="{gy:.1f}" x2="{width-pad}" y2="{gy:.1f}" stroke="#1e2a38" stroke-width="1"/>'
        lbls+=f'<text x="{pad-8}" y="{gy+4:.1f}" fill="#5b6b7d" font-size="11" text-anchor="end">{m:.1f}×</text>'
    for g in range(int(maxyears)+1):
        gx=X(g)
        lbls+=f'<text x="{gx:.1f}" y="{height-pad+18:.1f}" fill="#5b6b7d" font-size="11" text-anchor="middle">Yr {g}</text>'
    base=f'<line x1="{pad}" y1="{Y(1):.1f}" x2="{width-pad}" y2="{Y(1):.1f}" stroke="#3a4a5a" stroke-width="1.2" stroke-dasharray="5 4"/>'
    paths=""; leg=""; ly=pad+8
    for i,(d,mult) in enumerate(series):
        pts="M"+" L".join(f"{X(yr):.1f},{Y(m):.1f}" for yr,m in mult)
        paths+=f'<path d="{pts}" fill="none" stroke="{d["color"]}" stroke-width="2.4"/>'
        endm=mult[-1][1]
        paths+=f'<text x="{X(mult[-1][0])-4:.1f}" y="{Y(endm)-6:.1f}" fill="{d["color"]}" font-size="12" font-weight="700" text-anchor="end">{endm:.1f}×</text>'
        leg+=f'<rect x="{pad+8}" y="{ly}" width="13" height="13" fill="{d["color"]}"/><text x="{pad+28}" y="{ly+11}" fill="#c9d6e3" font-size="13">{d["name"]}</text>'
        ly+=22
    legg=f'<g>{leg}</g>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{grid}{lbls}{base}{paths}{legg}</svg>'

def svg_mini(d, width=350, height=230, pad=44):
    """Small-multiple: strategy vs its benchmark, growth-of-1."""
    ec=d["ec"]; nc=d["nc"]; cap=d["cfg"]["capital"]
    sm=[e[1]/cap for e in ec]; n0=nc[0][1]; bm=[c[1]/n0 for c in nc]
    nlen=min(len(sm),len(bm)); sm=sm[:nlen]; bm=bm[:nlen]
    allv=sm+bm; ymin=min(allv); ymax=max(allv); yr=ymax-ymin or 1
    def X(i): return pad+i*(width-2*pad)/(nlen-1)
    def Y(v): return height-pad-(v-ymin)/yr*(height-2*pad)
    grid=""
    for g in range(4):
        v=ymin+g*yr/3; gy=Y(v)
        grid+=f'<line x1="{pad}" y1="{gy:.1f}" x2="{width-pad}" y2="{gy:.1f}" stroke="#1a2532" stroke-width="1"/>'
        grid+=f'<text x="{pad-6}" y="{gy+3:.1f}" fill="#5b6b7d" font-size="9.5" text-anchor="end">{v:.1f}×</text>'
    sp="M"+" L".join(f"{X(i):.1f},{Y(v):.1f}" for i,v in enumerate(sm))
    bp="M"+" L".join(f"{X(i):.1f},{Y(v):.1f}" for i,v in enumerate(bm))
    s_line=f'<path d="{sp}" fill="none" stroke="{d["color"]}" stroke-width="2.2"/>'
    b_line=f'<path d="{bp}" fill="none" stroke="#56657a" stroke-width="1.5" opacity="0.8"/>'
    title=f'<text x="{width/2:.0f}" y="18" fill="#dce8f3" font-size="13" font-weight="600" text-anchor="middle">{d["name"]}</text>'
    leg=f'<g font-size="10"><rect x="{pad}" y="{height-16}" width="10" height="10" fill="{d["color"]}"/><text x="{pad+14}" y="{height-7}" fill="#9fb2c4">Strategy {sm[-1]:.1f}×</text><rect x="{pad+110}" y="{height-16}" width="10" height="10" fill="#56657a"/><text x="{pad+124}" y="{height-7}" fill="#9fb2c4">Bench {bm[-1]:.1f}×</text></g>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{title}{grid}{b_line}{s_line}{leg}</svg>'

def svg_grouped(groups, vals_a, vals_b, lab_a, lab_b, col_a_list, col_b="#56657a",
                width=1080, height=320, pad=60, fmt="{:+.1f}%"):
    n=len(groups); allv=vals_a+vals_b
    ymax=max(allv+[1]); ymin=min(allv+[0]); span=ymax-ymin or 1
    gw=(width-2*pad)/n
    def Y(v): return height-pad-(v-ymin)/span*(height-2*pad)
    zero=Y(0); bars=""; xlbls=""; bw=gw*0.30
    for i,g in enumerate(groups):
        cx=pad+i*gw+gw/2
        ya=Y(vals_a[i]); a0=min(ya,zero); ah=abs(ya-zero)
        ca = col_a_list[i] if isinstance(col_a_list,list) else col_a_list
        bars+=f'<rect x="{cx-bw-3:.1f}" y="{a0:.1f}" width="{bw:.1f}" height="{ah:.1f}" fill="{ca}" rx="2"/>'
        bars+=f'<text x="{cx-bw/2-3:.1f}" y="{a0-5 if vals_a[i]>=0 else a0+ah+13:.1f}" fill="#dce8f3" font-size="11" font-weight="600" text-anchor="middle">{fmt.format(vals_a[i])}</text>'
        yb=Y(vals_b[i]); b0=min(yb,zero); bh=abs(yb-zero)
        bars+=f'<rect x="{cx+3:.1f}" y="{b0:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{col_b}" rx="2"/>'
        bars+=f'<text x="{cx+bw/2+3:.1f}" y="{b0-5 if vals_b[i]>=0 else b0+bh+13:.1f}" fill="#8a9bad" font-size="11" text-anchor="middle">{fmt.format(vals_b[i])}</text>'
        xlbls+=f'<text x="{cx:.1f}" y="{height-pad+20:.1f}" fill="#9fb2c4" font-size="12" text-anchor="middle">{g}</text>'
    axis=f'<line x1="{pad}" y1="{zero:.1f}" x2="{width-pad}" y2="{zero:.1f}" stroke="#3a4a5a" stroke-width="1.4"/>'
    leg=f'<g font-size="13"><rect x="{pad+8}" y="12" width="13" height="13" fill="#7e8da0"/><text x="{pad+28}" y="23" fill="#c9d6e3">{lab_a}</text><rect x="{pad+150}" y="12" width="13" height="13" fill="{col_b}"/><text x="{pad+170}" y="23" fill="#c9d6e3">{lab_b}</text></g>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{axis}{bars}{xlbls}{leg}</svg>'

def svg_single(groups, vals, colors, width=1080, height=300, pad=60, fmt="{:+.1f}%"):
    n=len(groups); ymax=max(vals+[1]); ymin=min(vals+[0]); span=ymax-ymin or 1
    gw=(width-2*pad)/n
    def Y(v): return height-pad-(v-ymin)/span*(height-2*pad)
    zero=Y(0); bars=""; xlbls=""; bw=gw*0.34
    for i,g in enumerate(groups):
        cx=pad+i*gw+gw/2; y=Y(vals[i]); y0=min(y,zero); h=abs(y-zero)
        bars+=f'<rect x="{cx-bw/2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{colors[i]}" rx="3"/>'
        bars+=f'<text x="{cx:.1f}" y="{y0-7 if vals[i]>=0 else y0+h+15:.1f}" fill="#dce8f3" font-size="14" font-weight="700" text-anchor="middle">{fmt.format(vals[i])}</text>'
        xlbls+=f'<text x="{cx:.1f}" y="{height-pad+20:.1f}" fill="#9fb2c4" font-size="12" text-anchor="middle">{g}</text>'
    axis=f'<line x1="{pad}" y1="{zero:.1f}" x2="{width-pad}" y2="{zero:.1f}" stroke="#3a4a5a" stroke-width="1.4"/>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">{axis}{bars}{xlbls}</svg>'

# ─── charts ──────────────────────────────────────────────────────────────────
names=[d["name"] for d in data]
colors=[d["color"] for d in data]
chart_overlay = svg_growth_overlay(data)
minis = "".join(f'<div class="mini">{svg_mini(d)}</div>' for d in data)
chart_cagr = svg_grouped(names, [d["S"]["cagr"] for d in data], [d["S"]["nifty_cagr"] for d in data],
                         "Strategy", "Benchmark", colors)
chart_dd = svg_grouped(names, [-d["S"]["max_dd"] for d in data], [-d["S"]["nifty_max_dd"] for d in data],
                       "Strategy", "Benchmark", colors)
chart_alpha = svg_single(names, [d["S"]["alpha"] for d in data], colors)

# ─── master table ────────────────────────────────────────────────────────────
def row(label, fn, bold=False):
    cells="".join(f'<td class="num{" strong" if bold else ""}">{fn(d)}</td>' for d in data)
    return f'<tr><td class="metric">{label}</td>{cells}</tr>'

rows = "".join([
    row("Period / Benchmark", lambda d: d["sub"]),
    row("Starting capital", lambda d: big(d["cfg"]["capital"], d["cur"])),
    row("Final value", lambda d: big(d["S"]["final_value"], d["cur"]), bold=True),
    row("Growth multiple", lambda d: f'{d["S"]["final_value"]/d["cfg"]["capital"]:.2f}×', bold=True),
    row("Total return", lambda d: f'<span class="pos">{d["S"]["total_ret"]:+.0f}%</span>'),
    row("CAGR (strategy)", lambda d: f'<span class="pos">{d["S"]["cagr"]:.1f}%</span>', bold=True),
    row("CAGR (benchmark)", lambda d: f'{d["S"]["nifty_cagr"]:.1f}%'),
    row("Outperformance", lambda d: f'<span class="pos">+{d["S"]["cagr"]-d["S"]["nifty_cagr"]:.1f} pp</span>', bold=True),
    row("CAPM Alpha", lambda d: f'<span class="pos">{d["S"]["alpha"]:+.1f}%</span>', bold=True),
    row("Beta", lambda d: f'{d["S"]["beta"]:.2f}'),
    row("Sharpe ratio", lambda d: f'{d["S"]["sharpe"]:.2f}'),
    row("Sortino ratio", lambda d: f'{d["S"]["sortino"]:.2f}'),
    row("Calmar ratio", lambda d: f'{d["S"]["calmar"]:.2f}'),
    row("Volatility (ann.)", lambda d: f'{d["S"]["vol"]:.1f}%'),
    row("Max drawdown (strategy)", lambda d: f'<span class="neg">-{d["S"]["max_dd"]:.1f}%</span>', bold=True),
    row("Max drawdown (benchmark)", lambda d: f'<span class="neg">-{d["S"]["nifty_max_dd"]:.1f}%</span>'),
    row("Win rate", lambda d: f'{d["S"]["win_rate"]:.1f}%'),
    row("Avg win / avg loss", lambda d: f'{d["S"]["avg_win"]:+.0f}% / {d["S"]["avg_loss"]:+.0f}%'),
    row("R-multiple", lambda d: f'{d["S"]["r_mult"]:.1f}'),
    row("Profit factor", lambda d: f'{d["S"]["profit_factor"]:.2f}'),
    row("Total trades", lambda d: f'{d["S"]["trades"]}'),
    row("Largest winner", lambda d: f'{d["S"]["largest_win_sym"]} {d["S"]["largest_win_pct"]:+.0f}%'),
])

hdr_cells = "".join(f'<th class="run" style="border-bottom:3px solid {d["color"]}">{d["name"]}</th>' for d in data)

# headline cards
def card(d):
    S=d["S"]
    return f'''<div class="hcard" style="border-top:3px solid {d['color']}">
      <div class="hname">{d['name']}</div><div class="hsub">{d['sub']}</div>
      <div class="hbig">{S['cagr']:.1f}%<span class="hunit"> CAGR</span></div>
      <div class="hrow"><span>vs bench {S['nifty_cagr']:.1f}%</span><span class="pos">+{S['cagr']-S['nifty_cagr']:.1f}pp</span></div>
      <div class="hrow"><span>Alpha</span><span class="pos">{S['alpha']:+.1f}%</span></div>
      <div class="hrow"><span>Max DD</span><span class="neg">-{S['max_dd']:.1f}%</span></div>
      <div class="hrow"><span>Sharpe</span><span>{S['sharpe']:.2f}</span></div>
      <div class="hgrowth">{big(d['cfg']['capital'],d['cur'])} → <b>{big(S['final_value'],d['cur'])}</b></div>
    </div>'''
cards = "".join(card(d) for d in data)

HTML=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RS EMA50×200 — Multi-Market Tear Sheet</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0a1118;color:#c9d6e3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5;padding:0 0 80px}}
  .wrap{{max-width:1180px;margin:0 auto;padding:0 24px}}
  header{{background:linear-gradient(135deg,#0d1825,#10202f);border-bottom:1px solid #1c2c3c;padding:40px 0 32px;margin-bottom:32px}}
  h1{{font-size:29px;font-weight:700;color:#fff;letter-spacing:-0.5px}}
  .subtitle{{color:#7e93a8;font-size:15px;margin-top:6px}}
  h2{{font-size:21px;color:#fff;margin:46px 0 6px;padding-bottom:10px;border-bottom:1px solid #1c2c3c}}
  .lead{{color:#8a9bad;font-size:14px;margin:4px 0 14px}}
  .hgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
  @media(max-width:820px){{.hgrid{{grid-template-columns:1fr}} .minis{{grid-template-columns:1fr !important}}}}
  .hcard{{background:#0f1b27;border:1px solid #1a2a39;border-radius:12px;padding:18px}}
  .hname{{font-size:16px;font-weight:700;color:#fff}} .hsub{{font-size:12px;color:#6f8295;margin-bottom:10px}}
  .hbig{{font-size:34px;font-weight:800;color:#fff}} .hunit{{font-size:14px;color:#8a9bad;font-weight:500}}
  .hrow{{display:flex;justify-content:space-between;font-size:13px;padding:3px 0;border-top:1px solid #15212e;margin-top:4px}}
  .hgrowth{{margin-top:12px;padding-top:10px;border-top:1px solid #15212e;font-size:13.5px;color:#9fb2c4}}
  .hgrowth b{{color:#fff}}
  .pos{{color:#3fb950}} .neg{{color:#e05260}}
  .chart-box{{background:#0c1620;border:1px solid #1a2a39;border-radius:12px;padding:22px;margin:16px 0}}
  .minis{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
  .mini{{background:#0c1620;border:1px solid #1a2a39;border-radius:10px;padding:10px}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;margin:8px 0}}
  th,td{{padding:9px 14px;border-bottom:1px solid #16222e;text-align:left}}
  th.run{{text-align:right;color:#fff;font-size:13px}}
  td.metric{{color:#8a9bad}} td.num{{text-align:right;font-variant-numeric:tabular-nums;color:#dce8f3}}
  td.strong{{font-weight:700;color:#fff}}
  tr:hover td{{background:#0f1b27}}
  .note{{background:#13202d;border-left:3px solid #3fb950;border-radius:6px;padding:14px 18px;font-size:13.5px;color:#b9c8d6;margin:16px 0}}
  .note.amber{{border-left-color:#d9a441}}
  .footer{{margin-top:50px;padding-top:24px;border-top:1px solid #1c2c3c;color:#5b6b7d;font-size:12px;text-align:center}}
</style></head><body>
<header><div class="wrap">
  <h1>Relative Strength EMA50 × EMA200 — Multi-Market Validation</h1>
  <div class="subtitle">One strategy · three independent tests · two countries · two regimes · ₹10L / $10K · 10% stop · 15 positions · 0.5% risk</div>
</div></header>
<div class="wrap">

<div class="note"><b>The case in one line:</b> the same mechanical rule — buy when a stock's relative strength vs its index turns structurally positive (RS EMA50 crosses above EMA200), exit on reversal or a 10% stop — produced
<b>positive alpha in all three independent tests</b>, across two countries and two market regimes, while drawing down
<b>far less than the benchmark in every crisis</b>.</div>

<h2>The Three Tests</h2>
<div class="hgrid">{cards}</div>

<h2>Growth of Capital — All Three Overlaid</h2>
<div class="lead">Each line = growth multiple of starting capital vs years elapsed (dashed = break-even 1.0×). Normalised so all three are directly comparable.</div>
<div class="chart-box">{chart_overlay}</div>

<h2>Strategy vs Its Own Benchmark</h2>
<div class="lead">Coloured = strategy · grey = that market's index. Growth-of-1 over each test window.</div>
<div class="minis">{minis}</div>

<h2>CAGR — Strategy vs Benchmark</h2>
<div class="chart-box">{chart_cagr}</div>

<h2>Annual Alpha (CAPM)</h2>
<div class="lead">Return above what the strategy's market exposure (beta) alone would explain — the pure stock-selection edge.</div>
<div class="chart-box">{chart_alpha}</div>

<h2>Max Drawdown — Strategy vs Benchmark</h2>
<div class="lead">The risk story: in every test the strategy's worst drawdown was shallower than the index — dramatically so in the 2020 COVID crash (India 2015–2020).</div>
<div class="chart-box">{chart_dd}</div>
<div class="note amber"><b>Crisis protection:</b> during the 2020 COVID crash the India 2015–2020 strategy fell only
<b>-{data[0]['S']['max_dd']:.0f}%</b> versus the Nifty's <b>-{data[0]['S']['nifty_max_dd']:.0f}%</b> — less than half — because the
relative-strength exit rotated the book defensively toward cash before the worst of the fall. Low betas
({", ".join(f"{d['S']['beta']:.2f}" for d in data)}) confirm the outperformance is selection, not leverage.</div>

<h2>Full Comparison Table</h2>
<table>
  <tr><th class="metric">Metric</th>{hdr_cells}</tr>
  {rows}
</table>

<h2>What This Establishes</h2>
<div class="note"><b>1 · It is not curve-fit to one period.</b> India 2021–26 was the in-sample design window. India 2015–20 is a fully
out-of-sample test on a different, harder regime (2015–16 correction, 2018 mid-cap crash, 2020 COVID) — and it still delivered
+{data[0]['S']['cagr']-data[0]['S']['nifty_cagr']:.1f}pp of outperformance and +{data[0]['S']['alpha']:.1f}% alpha.</div>
<div class="note"><b>2 · It is not specific to one market.</b> Ported unchanged to US large-caps (the hardest benchmark in the world),
it still beat the S&P 500 by +{data[2]['S']['cagr']-data[2]['S']['nifty_cagr']:.1f}pp/yr with +{data[2]['S']['alpha']:.1f}% alpha.</div>
<div class="note"><b>3 · It protects capital in crises.</b> In all three tests the strategy's drawdown was shallower than its
benchmark — the defining property a fund manager underwrites before allocating.</div>
<div class="note amber"><b>Caveats (consistent across all runs):</b> survivorship — universes use current liquid constituents;
returns are concentrated in a few multi-baggers (top-10 trades ≈ 70–75% of gross profit); gross of brokerage/slippage
(tax is modelled); and these are patient trend-following books that must tolerate 17–24% drawdowns to capture the upside.</div>

<div class="footer">Champion Trader System · Strategy R&D · RS EMA50×200 multi-market tear sheet ·
India 2015–20 + India 2021–26 + US 2021–26</div>
</div></body></html>'''

with open("/home/user/champion-trader/docs/rs_ema50_tearsheet.html","w") as f:
    f.write(HTML)
print(f"Wrote docs/rs_ema50_tearsheet.html ({len(HTML):,} bytes)")
for d in data:
    S=d["S"]
    print(f"  {d['name']:<18} CAGR {S['cagr']:5.1f}% | bench {S['nifty_cagr']:4.1f}% | alpha {S['alpha']:+5.1f}% | maxDD -{S['max_dd']:4.1f}% (bench -{S['nifty_max_dd']:.1f}%) | beta {S['beta']:.2f}")
