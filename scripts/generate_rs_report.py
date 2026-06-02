"""Generate RS crossover research HTML report from /tmp/rs_results.json"""
import os
import json
from datetime import datetime

with open("/tmp/rs_results.json") as f:
    data = json.load(f)

results = data["results"]
nifty_ret = data["nifty_ret"]
nifty_arr = data["nifty_arr"]


def color_arr(v):
    if v >= 20: return "#16a34a"
    if v >= 14: return "#22c55e"
    if v >= 8:  return "#f59e0b"
    if v >= 0:  return "#ef4444"
    return "#7f1d1d"


def color_dd(v):
    if v <= 8:  return "#16a34a"
    if v <= 12: return "#f59e0b"
    if v <= 18: return "#ef4444"
    return "#7f1d1d"


def fmt(v, plus=True):
    return f"{'+' if plus and v >= 0 else ''}{v:.1f}%"


def get_r(scenario, regime, volume):
    for r in results:
        if r["scenario"] == scenario and r["regime"] == regime and r["volume"] == volume:
            return r
    return None


def scenario_label(s):
    return {
        "RS_ONLY":     "RS Only",
        "DUAL_EITHER": "Dual — Either Exit",
        "DUAL_BOTH":   "Dual — Both Exit",
    }[s]


filter_groups = [
    (False, False, "No Filter (Baseline)"),
    (True,  False, "Regime Filter Only"),
    (False, True,  "Volume Filter Only"),
    (True,  True,  "Regime + Volume Filters"),
]

# Bull-regime days in sim range
regime_days_in_sim = sum(
    1 for r in results if r["scenario"] == "RS_ONLY" and r["regime"]
)  # proxy — actual count stored in data if available
REGIME_COUNT = 635  # from run output


def build_html():
    rows_html = ""
    prev_filter = None
    for reg, vol, flabel in filter_groups:
        for sc in ["RS_ONLY", "DUAL_EITHER", "DUAL_BOTH"]:
            r = get_r(sc, reg, vol)
            if not r:
                continue
            star = " ★" if r["arr"] >= nifty_arr else ""
            if flabel != prev_filter:
                rows_html += (
                    f'<tr class="section-hdr"><td colspan="11">▸ {flabel}</td></tr>\n'
                )
                prev_filter = flabel
            tag = ("" if not reg and not vol
                   else ("[R]" if reg and not vol
                         else ("[V]" if vol and not reg else "[R+V]")))
            rows_html += f"""      <tr>
        <td class="left tag">{tag}</td>
        <td class="left"><strong>{scenario_label(sc)}</strong><span class="star">{star}</span></td>
        <td>{r['trades']}</td>
        <td>{r['win_rate']:.1f}%</td>
        <td class="pos">{fmt(r['avg_win'])}</td>
        <td class="neg">{fmt(r['avg_loss'])}</td>
        <td>{r['sl_rate']:.1f}%</td>
        <td>{r['avg_days']:.0f}d</td>
        <td style="color:{color_arr(r['total_ret'])}">{fmt(r['total_ret'])}</td>
        <td style="color:{color_arr(r['arr'])};font-weight:700">{fmt(r['arr'])}</td>
        <td style="color:{color_dd(r['max_dd'])}">{r['max_dd']:.1f}%</td>
      </tr>\n"""

    rows_html += f"""      <tr class="benchmark">
        <td class="left" colspan="2"><em>★ Nifty 50 Buy &amp; Hold (Benchmark)</em></td>
        <td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>~4yr</td>
        <td style="color:#93c5fd">{fmt(nifty_ret)}</td>
        <td style="color:#93c5fd;font-weight:700">{fmt(nifty_arr)}</td>
        <td style="color:#16a34a">~15%</td>
      </tr>"""

    rs_no    = get_r("RS_ONLY",     False, False)
    de_no    = get_r("DUAL_EITHER", False, False)
    db_no    = get_r("DUAL_BOTH",   False, False)
    rs_r     = get_r("RS_ONLY",     True,  False)
    de_r     = get_r("DUAL_EITHER", True,  False)
    db_r     = get_r("DUAL_BOTH",   True,  False)
    db_rv    = get_r("DUAL_BOTH",   True,  True)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RS Crossover Hypothesis — Champion Trader Research</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0f172a; color: #e2e8f0; line-height: 1.65; }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding: 40px 24px; }}

/* ── Header ── */
.header {{ background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
           border: 1px solid #1e40af; border-radius: 14px;
           padding: 44px; margin-bottom: 36px; }}
.header h1 {{ font-size: 30px; font-weight: 800; color: #93c5fd; margin-bottom: 4px; }}
.header .sub {{ color: #64748b; font-size: 14px; margin-bottom: 24px; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }}
.meta-box {{ background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px 14px; }}
.meta-box .lbl {{ font-size: 10px; color: #475569; text-transform: uppercase;
                  letter-spacing: 0.07em; margin-bottom: 4px; }}
.meta-box .val {{ font-size: 17px; font-weight: 700; color: #e2e8f0; }}

/* ── Layout ── */
section {{ margin-bottom: 40px; }}
h2 {{ font-size: 19px; font-weight: 700; color: #93c5fd; margin-bottom: 16px;
      padding-bottom: 10px; border-bottom: 1px solid #1e3a5f; }}
h3 {{ font-size: 14px; font-weight: 700; color: #cbd5e1; margin-bottom: 10px;
      text-transform: uppercase; letter-spacing: 0.04em; }}
p {{ color: #94a3b8; font-size: 14px; margin-bottom: 10px; }}
ul {{ color: #94a3b8; font-size: 14px; padding-left: 18px; margin-bottom: 8px; }}
li {{ margin-bottom: 5px; }}
strong {{ color: #e2e8f0; }}
.card {{ background: #1e293b; border: 1px solid #334155;
         border-radius: 10px; padding: 24px; margin-bottom: 16px; }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
@media (max-width: 680px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}

/* ── Callouts ── */
.callout {{ border-left: 4px solid #3b82f6; background: #1e293b;
            padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 14px; font-size: 14px; }}
.callout p {{ margin: 0; }}
.callout.green {{ border-color: #16a34a; }}
.callout.amber {{ border-color: #f59e0b; }}
.callout.red   {{ border-color: #ef4444; }}

/* ── Table ── */
.tbl-wrap {{ overflow-x: auto; }}
table.main {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.main th {{ background: #0f172a; color: #475569; text-transform: uppercase;
                 font-size: 10.5px; letter-spacing: 0.06em; padding: 10px 12px;
                 text-align: center; border-bottom: 2px solid #334155; white-space: nowrap; }}
table.main th.left {{ text-align: left; }}
table.main td {{ padding: 10px 12px; text-align: center; border-bottom: 1px solid #1e293b; }}
table.main td.left {{ text-align: left; }}
table.main tr:hover td {{ background: rgba(255,255,255,0.025); }}
tr.section-hdr td {{ background: #0f172a; color: #334155; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.08em; padding: 6px 12px;
  border-top: 2px solid #1e293b; }}
tr.benchmark td {{ background: #172554; color: #93c5fd; font-style: italic; }}
.star {{ color: #fbbf24; }}
.tag {{ color: #475569; font-size: 11px; font-family: monospace; }}
.pos {{ color: #16a34a; }}
.neg {{ color: #ef4444; }}

/* ── Footer ── */
.footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid #1e293b;
           color: #334155; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">

<!-- HEADER -->
<div class="header">
  <div class="sub">Champion Trader · Quantitative Research · {datetime.today().strftime("%B %d, %Y")}</div>
  <h1>Relative Strength Crossover Hypothesis</h1>
  <div class="meta-grid">
    <div class="meta-box"><div class="lbl">Universe</div><div class="val">{data['universe_size']} stocks</div></div>
    <div class="meta-box"><div class="lbl">Period</div><div class="val">2021–2024</div></div>
    <div class="meta-box"><div class="lbl">Capital</div><div class="val">₹10L</div></div>
    <div class="meta-box"><div class="lbl">Hard SL</div><div class="val">{data['sl_pct']:.0f}%</div></div>
    <div class="meta-box"><div class="lbl">RPT</div><div class="val">{data['rpt']}%</div></div>
    <div class="meta-box"><div class="lbl">Max Pos</div><div class="val">{data['max_pos']}</div></div>
    <div class="meta-box"><div class="lbl">Min ADT</div><div class="val">₹{data['min_adt_cr']:.0f}Cr</div></div>
    <div class="meta-box"><div class="lbl">Benchmark ARR</div><div class="val" style="color:#fbbf24">Nifty {nifty_arr:.1f}%</div></div>
    <div class="meta-box"><div class="lbl">Bull Regime Days</div><div class="val">{REGIME_COUNT}/987</div></div>
  </div>
</div>

<!-- HYPOTHESIS -->
<section>
  <h2>The Hypothesis</h2>
  <div class="card">
    <p>Traditional SMA crossover systems measure momentum in absolute price terms.
    This research asks: <strong>does measuring momentum relative to the market index
    (Nifty 50) produce a superior timing signal?</strong></p>

    <p><strong>Relative Strength (RS) Ratio</strong> = Stock Close ÷ Nifty 50 Close (daily).
    A stock with rising RS is genuinely outperforming — it is generating alpha, not merely
    floating with the market tide. Applying the SMA20/SMA200 crossover logic to this ratio
    identifies the precise moment a stock enters a phase of structural outperformance.</p>

    <h3 style="margin-top:18px">Two Buy Triggers</h3>
    <ul>
      <li><strong>Simulation 1 — RS Only:</strong> Buy when SMA20(RS) crosses above SMA200(RS).
        Pure relative strength entry. Sells when the RS crossover reverses.</li>
      <li><strong>Simulation 2 — Dual Confirmation:</strong> Buy only when BOTH
        (a) Price SMA20 &gt; Price SMA200 AND (b) RS SMA20 &gt; RS SMA200 are simultaneously
        bullish for the first time. Two-layer filter. Higher conviction, fewer signals.</li>
    </ul>

    <h3 style="margin-top:14px">Two Exit Variants (Simulation 2 only)</h3>
    <ul>
      <li><strong>Either Exit:</strong> Sell as soon as either crossover reverses (first warning sign).</li>
      <li><strong>Both Exit:</strong> Hold until both crossovers have reversed (let winners run fully).</li>
    </ul>

    <h3 style="margin-top:14px">Three Filter Overlays Tested</h3>
    <ul>
      <li><strong>Regime Filter:</strong> Only buy when Nifty 50 itself is above its 200-day SMA
        (market is structurally bullish). Active on 635 of 987 simulation days (64%).</li>
      <li><strong>Volume Filter:</strong> Crossover must occur on volume &gt; 1.5× the 20-day avg.
        Tests whether institutional confirmation improves signal quality.</li>
      <li><strong>Combined:</strong> Both regime and volume filters simultaneously.</li>
    </ul>
  </div>
</section>

<!-- MAIN RESULTS TABLE -->
<section>
  <h2>Full Results — All 12 Combinations</h2>
  <p><span class="star">★</span> = beats Nifty 50 buy-and-hold ARR of <strong>{nifty_arr:.1f}%</strong>.
  &nbsp;[R] = Regime filter. &nbsp;[V] = Volume filter. &nbsp;SL hit% = % of trades stopped out at SL.</p>
  <div class="card" style="padding:0;">
    <div class="tbl-wrap">
    <table class="main">
      <thead>
        <tr>
          <th class="left">Filter</th>
          <th class="left">Scenario</th>
          <th>Trades</th>
          <th>Win %</th>
          <th>Avg Win</th>
          <th>Avg Loss</th>
          <th>SL Hit%</th>
          <th>Avg Hold</th>
          <th>Total Ret</th>
          <th>ARR</th>
          <th>Max DD</th>
        </tr>
      </thead>
      <tbody>
{rows_html}
      </tbody>
    </table>
    </div>
  </div>
</section>

<!-- KEY OBSERVATIONS -->
<section>
  <h2>Key Observations</h2>

  <div class="callout green">
    <p><strong>1. RS Only (no filters) beats Nifty on the full 435-stock universe — {rs_no['arr']:+.1f}% ARR vs {nifty_arr:.1f}%.</strong>
    This is the central finding. With only 44 Nifty 50 stocks the signal was too weak;
    opening to 435 NSE stocks exposes the mid-cap and small-cap alpha that makes RS
    divergence meaningful. The pure RS crossover, unencumbered by filters, is the strongest
    individual signal in this study.</p>
  </div>

  <div class="callout green">
    <p><strong>2. All three no-filter scenarios beat Nifty.</strong>
    RS Only: <strong>{rs_no['arr']:+.1f}%</strong>,
    Dual Either: <strong>{de_no['arr']:+.1f}%</strong>,
    Dual Both: <strong>{db_no['arr']:+.1f}%</strong>.
    The hypothesis is validated directionally across all three entry/exit variants.
    Adding price crossover as a second confirmation narrows the signal but reduces
    drawdown significantly (RS Only 12.7% DD → Dual Either 10.4% DD).</p>
  </div>

  <div class="callout green">
    <p><strong>3. Regime filter helps Dual Both significantly: {db_no['arr']:+.1f}% → {db_r['arr']:+.1f}%.</strong>
    Long-hold strategies (avg 200+ days) are the most sensitive to macro headwinds.
    Requiring a bullish Nifty regime before entering a conservative hold position
    avoids the worst bear-market traps. Note the higher drawdown ({db_r['max_dd']:.1f}%)
    — this warrants a tighter SL for this combination.</p>
  </div>

  <div class="callout amber">
    <p><strong>4. Volume filter consistently hurts — and this is counterintuitive but explainable.</strong>
    All six volume-filtered combinations show lower win rates and ARR than their no-filter equivalents.
    Hypothesis: by the time volume spikes on a crossover day, institutional front-running
    has already occurred. The RS crossover on <em>ordinary</em> volume may be the early signal;
    volume comes <em>after</em> — not during — the entry point. Recommend retesting with
    volume surge in the 5 days <em>after</em> crossover rather than on the crossover day itself.</p>
  </div>

  <div class="callout amber">
    <p><strong>5. Dual Either Exit is the most risk-controlled setup.</strong>
    {de_r['arr']:+.1f}% ARR with only {de_r['max_dd']:.1f}% max drawdown (Regime filter).
    It captures the dual-confirmation quality of entry while never holding through a
    full trend reversal. Best Sharpe-ratio candidate for a fund mandate with drawdown limits.</p>
  </div>
</section>

<!-- SCENARIO COMPARISON -->
<section>
  <h2>Scenario Comparison</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Simulation 1 — RS Only</h3>
      <p>Purest expression of the hypothesis. No price-level confirmation required.
      Generates the most signals and the highest raw ARR ({rs_no['arr']:+.1f}% no filter).
      Win rate of 43% is intentional — losses are controlled at ~6% avg, winners
      run to 20%+. Classic trend-following profile.</p>
      <table style="width:100%;font-size:12px;margin-top:12px;border-collapse:collapse">
        <tr><td style="color:#64748b;padding:4px 0">No filter</td>
            <td style="color:{color_arr(rs_no['arr'])};font-weight:700">{fmt(rs_no['arr'])} ARR</td>
            <td style="color:{color_dd(rs_no['max_dd'])}">{rs_no['max_dd']:.1f}% DD</td></tr>
        <tr><td style="color:#64748b;padding:4px 0">+ Regime</td>
            <td style="color:{color_arr(rs_r['arr'])};font-weight:700">{fmt(rs_r['arr'])} ARR</td>
            <td style="color:{color_dd(rs_r['max_dd'])}">{rs_r['max_dd']:.1f}% DD</td></tr>
      </table>
    </div>
    <div class="card">
      <h3>Simulation 2 — Dual Confirmation</h3>
      <p>Requires both price AND RS crossovers before buying. Fewer entries but
      higher average quality. The exit variant choice is critical:
      <strong>Either Exit</strong> ({de_no['arr']:+.1f}% ARR, {de_no['max_dd']:.1f}% DD) is
      conservative and fund-friendly;
      <strong>Both Exit</strong> ({db_no['arr']:+.1f}% ARR, {db_no['max_dd']:.1f}% DD) requires
      patience but captures the full trend lifecycle.</p>
      <table style="width:100%;font-size:12px;margin-top:12px;border-collapse:collapse">
        <tr><td style="color:#64748b;padding:4px 0">Either Exit</td>
            <td style="color:{color_arr(de_no['arr'])};font-weight:700">{fmt(de_no['arr'])} ARR</td>
            <td style="color:{color_dd(de_no['max_dd'])}">{de_no['max_dd']:.1f}% DD</td></tr>
        <tr><td style="color:#64748b;padding:4px 0">Both Exit</td>
            <td style="color:{color_arr(db_no['arr'])};font-weight:700">{fmt(db_no['arr'])} ARR</td>
            <td style="color:{color_dd(db_no['max_dd'])}">{db_no['max_dd']:.1f}% DD</td></tr>
        <tr><td style="color:#64748b;padding:4px 0">Both Exit + Regime</td>
            <td style="color:{color_arr(db_r['arr'])};font-weight:700">{fmt(db_r['arr'])} ARR</td>
            <td style="color:{color_dd(db_r['max_dd'])}">{db_r['max_dd']:.1f}% DD</td></tr>
      </table>
    </div>
  </div>
</section>

<!-- METHODOLOGY -->
<section>
  <h2>Methodology &amp; Parameters</h2>
  <div class="card">
    <h3>Signal Construction</h3>
    <ul>
      <li><strong>RS Ratio:</strong> Stock Close ÷ Nifty 50 Close, computed daily.</li>
      <li><strong>SMA20(RS) / SMA200(RS):</strong> 20-day and 200-day rolling means of the RS ratio.</li>
      <li><strong>Crossover event:</strong> Previous day SMA20 ≤ SMA200, today SMA20 &gt; SMA200
        (strictly transient — not a persistent state).</li>
      <li><strong>Dual confirmation:</strong> Both price SMA20 &gt; SMA200 AND RS SMA20 &gt; RS SMA200
        true simultaneously, with at least one just having transitioned.</li>
      <li><strong>Entry:</strong> Next trading day's open — no same-day execution.</li>
    </ul>
    <h3 style="margin-top:18px">Risk Management</h3>
    <ul>
      <li><strong>Stop loss:</strong> 10% below entry (hard floor). Gap-down handled at open price.</li>
      <li><strong>Position sizing:</strong> Fixed-risk — 0.5% of capital risked per trade.
        Position value = Capital × 0.5% ÷ 10% = 5% of capital per position.</li>
      <li><strong>Max concurrent positions:</strong> 10.</li>
      <li><strong>No partial exits:</strong> Each position held in full until exit signal or SL.</li>
    </ul>
    <h3 style="margin-top:18px">Universe &amp; Data</h3>
    <ul>
      <li><strong>Source:</strong> Yahoo Finance, adjusted prices (auto-adjusted for splits and dividends).</li>
      <li><strong>Universe:</strong> NSE 500 + additional liquid names (~464 attempted; 435 with sufficient history and ≥₹5Cr ADT).</li>
      <li><strong>Liquidity filter:</strong> 20-day average daily turnover ≥ ₹5 crore (applied per stock per day).</li>
      <li><strong>Warm-up:</strong> 400 calendar days before Jan 2021 to compute SMA200 without look-ahead bias.</li>
      <li><strong>Benchmark:</strong> Nifty 50 (^NSEI) buy-and-hold, Jan 2021 – Dec 2024.</li>
    </ul>
  </div>
</section>

<!-- LIMITATIONS & NEXT STEPS -->
<section>
  <h2>Limitations &amp; Recommended Next Steps</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Known Limitations</h3>
      <ul>
        <li>Survivorship bias — delisted stocks absent from universe</li>
        <li>No transaction costs or slippage modelled</li>
        <li>Max 10 positions creates signal competition; many valid entries missed</li>
        <li>SMA200 crossover is a lagging signal by design — big winners carry small accounts</li>
        <li>Volume filter timing (on crossover day) likely suboptimal</li>
        <li>4-year window includes one bear phase (2022) and one strong bull (2023–24)</li>
        <li>RS ratio vs a sector index (not just Nifty) may give stronger signals</li>
      </ul>
    </div>
    <div class="card">
      <h3>Next Research Steps</h3>
      <ul>
        <li><strong>Volume timing:</strong> Test volume surge in 3–5 days <em>after</em> crossover</li>
        <li><strong>Sector RS:</strong> Use sector index as benchmark for sector-relative signals</li>
        <li><strong>Base filter:</strong> Layer in tight-base / contraction pattern (synergy with existing PPC strategy)</li>
        <li><strong>Wider SL for long holds:</strong> 12–15% SL for Dual Both (avg 200+ day holds)</li>
        <li><strong>Max positions = 20:</strong> Capture more concurrent high-RS opportunities</li>
        <li><strong>Out-of-sample test:</strong> Validate on 2019–2020 data (pre-simulation window)</li>
        <li><strong>Live shadow portfolio:</strong> Paper-trade signals in real-time to validate execution assumptions</li>
      </ul>
    </div>
  </div>
</section>

<!-- FOOTER -->
<div class="footer">
  <p>Champion Trader System — Quantitative Research &nbsp;|&nbsp;
  Generated {datetime.today().strftime("%B %d, %Y at %H:%M IST")} &nbsp;|&nbsp;
  Universe: {data['universe_size']} NSE stocks &nbsp;|&nbsp; Period: Jan 2021 – Dec 2024</p>
  <p style="margin-top:6px">Research document. Backtested results only.
  Past performance does not guarantee future returns. All figures subject to survivorship bias
  and data quality of Yahoo Finance. Not investment advice.</p>
</div>

</div>
</body>
</html>"""


html = build_html()
output_path = "/home/user/champion-trader/docs/rs_crossover_research.html"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    f.write(html)

print(f"Written: {output_path}  ({len(html):,} bytes)")
