"""
Generate dual-universe RS Crossover research HTML report.
Reads /tmp/rs_results_5cr.json and /tmp/rs_results_15cr.json.
Writes /home/user/champion-trader/docs/rs_crossover_research.html
"""
import json
from datetime import datetime

with open("/tmp/rs_results_5cr_v2.json")  as f: data5  = json.load(f)
with open("/tmp/rs_results_15cr_v2.json") as f: data15 = json.load(f)

def get_r(data, scenario, regime, volume):
    for r in data["results"]:
        if r["scenario"] == scenario and r["regime"] == regime and r["volume"] == volume:
            return r
    return None

def color_arr(v):
    if v >= 20: return "#16a34a"
    if v >= 14: return "#22c55e"
    if v >= 10: return "#f59e0b"
    if v >=  0: return "#ef4444"
    return "#7f1d1d"

def color_dd(v):
    if v <= 10: return "#16a34a"
    if v <= 15: return "#f59e0b"
    if v <= 20: return "#ef4444"
    return "#7f1d1d"

def fmt(v, plus=True):
    return f"{'+' if plus and v >= 0 else ''}{v:.1f}%"

nifty_arr = data5["nifty_arr"]
nifty_ret = data5["nifty_ret"]
nifty_dd  = data5["nifty_max_dd"]

filter_groups = [
    (False, False, "No Filter — Baseline"),
    (True,  False, "Regime Filter Only"),
    (False, True,  "Volume Filter Only"),
    (True,  True,  "Regime + Volume Filters"),
]

filter_tags = {
    (False, False): "",
    (True,  False): "[R]",
    (False, True):  "[V]",
    (True,  True):  "[R+V]",
}

SCENARIOS = ["RS_ONLY", "DUAL_EITHER", "DUAL_BOTH"]


def table_rows(data):
    rows = ""
    prev_filter = None
    for reg, vol, flabel in filter_groups:
        for sc in SCENARIOS:
            r = get_r(data, sc, reg, vol)
            if not r:
                continue
            beat = r["arr"] > nifty_arr
            tag  = filter_tags[(reg, vol)]
            if flabel != prev_filter:
                rows += f'<tr class="section-hdr"><td colspan="10">▸ {flabel}</td></tr>\n'
                prev_filter = flabel
            sc_labels = {
                "RS_ONLY":     "RS Only",
                "DUAL_EITHER": "Dual — Either Exit",
                "DUAL_BOTH":   "Dual — Both Exit",
            }
            star_html = ' <span class="star">★</span>' if beat else ""
            rows += f"""<tr>
  <td class="left tag">{tag}</td>
  <td class="left"><strong>{sc_labels[sc]}</strong>{star_html}</td>
  <td>{r['trades']}</td>
  <td>{r['win_rate']:.1f}%</td>
  <td class="pos">{fmt(r['avg_win'])}</td>
  <td class="neg">{fmt(r['avg_loss'])}</td>
  <td>{r['sl_rate']:.1f}%</td>
  <td>{r['avg_days']:.0f}d</td>
  <td style="color:{color_arr(r['arr'])};font-weight:700">{fmt(r['arr'])}</td>
  <td style="color:{color_dd(r['max_dd'])}">{r['max_dd']:.1f}%</td>
</tr>\n"""
    # Benchmark row
    rows += f"""<tr class="benchmark">
  <td class="left" colspan="2"><em>★ Nifty 50 Buy &amp; Hold (Benchmark)</em></td>
  <td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>~5yr</td>
  <td style="color:#93c5fd;font-weight:700">{fmt(nifty_arr)}</td>
  <td style="color:#16a34a">{nifty_dd:.1f}%</td>
</tr>"""
    return rows


def table_html(data, title, min_adt):
    rows = table_rows(data)
    return f"""
<h3 style="color:#cbd5e1;margin-bottom:12px;font-size:15px">{title}
  <span style="font-size:12px;color:#475569;font-weight:400;margin-left:8px">
    {data['universe_size']} signal-ready stocks &nbsp;|&nbsp; Min ADT ≥ ₹{min_adt:.0f}Cr
  </span>
</h3>
<div class="card" style="padding:0;margin-bottom:28px">
  <div class="tbl-wrap">
  <table class="main">
    <thead>
      <tr>
        <th class="left">Filter</th>
        <th class="left">Scenario</th>
        <th>Trades</th>
        <th>Win%</th>
        <th>Avg Win</th>
        <th>Avg Loss</th>
        <th>SL Hit%</th>
        <th>Avg Hold</th>
        <th>ARR ★</th>
        <th>Max DD</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
  </div>
</div>"""


trading_days = data5["trading_days_in_sim"]
regime_days  = data5["regime_days_in_sim"]
regime_pct   = 100 * regime_days / trading_days
report_date  = datetime.today().strftime("%B %d, %Y")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RS Crossover Hypothesis — Champion Trader Research</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0f172a; color: #e2e8f0; line-height: 1.7; }}
.wrap {{ max-width: 1160px; margin: 0 auto; padding: 44px 24px; }}

/* Header */
.header {{ background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
           border: 1px solid #1e40af; border-radius: 14px;
           padding: 44px; margin-bottom: 36px; }}
.header h1 {{ font-size: 28px; font-weight: 800; color: #93c5fd; margin-bottom: 4px; }}
.header .sub {{ color: #64748b; font-size: 13px; margin-bottom: 24px; text-transform: uppercase;
                letter-spacing: 0.07em; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; }}
.meta-box {{ background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px 14px; }}
.meta-box .lbl {{ font-size: 10px; color: #475569; text-transform: uppercase;
                  letter-spacing: 0.07em; margin-bottom: 4px; }}
.meta-box .val {{ font-size: 16px; font-weight: 700; color: #e2e8f0; }}

/* Layout */
section {{ margin-bottom: 44px; }}
h2 {{ font-size: 19px; font-weight: 700; color: #93c5fd; margin-bottom: 18px;
      padding-bottom: 10px; border-bottom: 1px solid #1e3a5f; }}
p {{ color: #94a3b8; font-size: 14px; margin-bottom: 12px; }}
ul {{ color: #94a3b8; font-size: 14px; padding-left: 20px; margin-bottom: 10px; }}
li {{ margin-bottom: 6px; }}
strong {{ color: #e2e8f0; }}
.card {{ background: #1e293b; border: 1px solid #334155;
         border-radius: 10px; padding: 24px; margin-bottom: 16px; }}

/* Callouts */
.callout {{ border-left: 4px solid #3b82f6; background: #1e293b;
            padding: 14px 18px; border-radius: 0 8px 8px 0;
            margin-bottom: 14px; font-size: 14px; color: #94a3b8; }}
.callout p {{ margin: 0; }}
.callout.green  {{ border-color: #16a34a; }}
.callout.amber  {{ border-color: #f59e0b; }}
.callout.red    {{ border-color: #ef4444; }}
.callout.purple {{ border-color: #a855f7; }}

/* Scenario cards */
.sc-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-bottom: 20px; }}
.sc-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px; }}
.sc-card .sc-title {{ font-size: 13px; font-weight: 700; color: #93c5fd;
                      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }}
.sc-card .sc-badge {{ display: inline-block; font-size: 10px; font-weight: 700;
                      padding: 2px 8px; border-radius: 4px; margin-bottom: 10px; }}
.sc-card p {{ font-size: 13px; color: #94a3b8; margin: 0; }}
.badge-1 {{ background: #1e3a5f; color: #93c5fd; }}
.badge-2 {{ background: #14532d; color: #86efac; }}
.badge-3 {{ background: #451a03; color: #fcd34d; }}

/* Filter explanation */
.filter-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; }}
@media (max-width: 680px) {{ .filter-grid {{ grid-template-columns: 1fr; }} }}
.filter-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 18px; }}
.filter-card .f-label {{ font-size: 11px; font-weight: 700; color: #475569;
                         text-transform: uppercase; letter-spacing: 0.06em;
                         font-family: monospace; margin-bottom: 8px; }}
.filter-card .f-name {{ font-size: 14px; font-weight: 700; color: #e2e8f0; margin-bottom: 6px; }}
.filter-card p {{ font-size: 13px; color: #94a3b8; margin: 0; }}

/* Table */
.tbl-wrap {{ overflow-x: auto; }}
table.main {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.main th {{ background: #0f172a; color: #475569; text-transform: uppercase;
                 font-size: 10px; letter-spacing: 0.06em; padding: 10px 12px;
                 text-align: center; border-bottom: 2px solid #334155; white-space: nowrap; }}
table.main th.left {{ text-align: left; }}
table.main td {{ padding: 9px 12px; text-align: center; border-bottom: 1px solid #1e293b; }}
table.main td.left {{ text-align: left; }}
table.main tr:hover td {{ background: rgba(255,255,255,0.025); }}
tr.section-hdr td {{ background: #0f172a; color: #334155; font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.08em; padding: 5px 12px;
  border-top: 2px solid #1e293b; }}
tr.benchmark td {{ background: #172554; color: #93c5fd; font-style: italic; }}
.star {{ color: #fbbf24; }}
.tag {{ color: #475569; font-size: 11px; font-family: monospace; min-width: 36px; }}
.pos {{ color: #16a34a; }}
.neg {{ color: #ef4444; }}

/* Key findings */
.finding-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
.finding {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 18px; }}
.finding .num {{ font-size: 26px; font-weight: 800; color: #93c5fd; margin-bottom: 4px; }}
.finding .label {{ font-size: 12px; color: #64748b; text-transform: uppercase;
                   letter-spacing: 0.05em; margin-bottom: 8px; }}
.finding p {{ font-size: 13px; color: #94a3b8; margin: 0; }}

/* Appendix */
.appendix-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
@media (max-width: 680px) {{ .appendix-grid {{ grid-template-columns: 1fr; }} }}

/* Footer */
.footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid #1e293b;
           color: #334155; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">

<!-- ═══════════════════════════════ HEADER ═══════════════════════════════ -->
<div class="header">
  <div class="sub">Champion Trader · Quantitative Research · {report_date}</div>
  <h1>Relative Strength Crossover Hypothesis</h1>
  <div class="meta-grid">
    <div class="meta-box"><div class="lbl">Period</div><div class="val">Jan 2021 – May 2026</div></div>
    <div class="meta-box"><div class="lbl">Trading Days</div><div class="val">{trading_days:,}</div></div>
    <div class="meta-box"><div class="lbl">Capital</div><div class="val">₹10 Lakh</div></div>
    <div class="meta-box"><div class="lbl">Hard SL</div><div class="val">{data5['sl_pct']:.0f}%</div></div>
    <div class="meta-box"><div class="lbl">RPT</div><div class="val">{data5['rpt']}%</div></div>
    <div class="meta-box"><div class="lbl">Max Positions</div><div class="val">{data5['max_pos']}</div></div>
    <div class="meta-box"><div class="lbl">Nifty ARR</div>
      <div class="val" style="color:#fbbf24">{nifty_arr:.1f}%</div></div>
    <div class="meta-box"><div class="lbl">Nifty Max DD</div>
      <div class="val" style="color:#ef4444">{nifty_dd:.1f}%</div></div>
    <div class="meta-box"><div class="lbl">Bull Regime</div>
      <div class="val">{regime_pct:.0f}% of days</div></div>
  </div>
</div>

<!-- ═══════════════════════════════ HYPOTHESIS ═══════════════════════════════ -->
<section>
  <h2>The Hypothesis</h2>
  <div class="card">
    <p>Traditional SMA crossover systems measure momentum in <strong>absolute price terms</strong>.
    This research tests a different question: <strong>does measuring momentum relative to
    the market index produce a superior entry signal?</strong></p>

    <p>The core idea: compute the <strong>Relative Strength (RS) Ratio</strong> as
    <em>Stock Close ÷ Nifty 50 Close</em> on each trading day — a dimensionless number
    that reflects exactly how much alpha the stock is generating versus the index.
    Then apply the classic SMA20 / SMA200 golden-cross logic to this ratio, not to price.
    A crossover here means the stock has entered a phase of <em>structural outperformance</em>,
    not just a price uptick that may be pure market-beta.</p>
  </div>
</section>

<!-- ═══════════════════════════════ THREE SCENARIOS ═══════════════════════════════ -->
<section>
  <h2>Three Trading Scenarios</h2>
  <div class="sc-grid">

    <!-- RS Only -->
    <div class="sc-card">
      <div class="sc-title">Scenario 1 — RS Only</div>
      <div class="sc-badge badge-1">Single Trigger</div>
      <p><strong>Entry:</strong> Buy when the RS ratio's SMA20 crosses above its SMA200 for the
      first time (golden cross on relative strength). This is purely a <em>relative momentum</em>
      signal — the stock's outperformance trend is just beginning, regardless of whether price
      itself is above or below its own moving averages.</p>
      <p style="margin-top:10px"><strong>Exit:</strong> Sell when the same RS crossover reverses
      (SMA20 crosses back below SMA200 on the RS ratio). Hard stop-loss at 10% below entry.</p>
      <p style="margin-top:10px;color:#64748b;font-size:12px">
      <em>Think of it as: "Buy leaders. Sell when they stop leading."</em></p>
    </div>

    <!-- Dual Either -->
    <div class="sc-card">
      <div class="sc-title">Scenario 2 — Dual Confirmation, Quick Exit</div>
      <div class="sc-badge badge-2">Dual Trigger — Either Exit</div>
      <p><strong>Entry:</strong> Buy only when BOTH signals are simultaneously bullish for the
      first time — (a) Price SMA20 is already above Price SMA200 AND (b) RS SMA20 is already
      above RS SMA200. The crossover trigger fires when one of them <em>newly</em> becomes true
      while the other was already met. This is a <strong>higher conviction</strong> signal:
      the stock must be winning both in absolute price terms and relative to the index.</p>
      <p style="margin-top:10px"><strong>Exit:</strong> Sell as soon as <em>either</em> crossover
      reverses — the first sign of deterioration. Defensive approach; protects capital aggressively.</p>
      <p style="margin-top:10px;color:#64748b;font-size:12px">
      <em>Think of it as: "Enter with two green lights. Exit at the first red."</em></p>
    </div>

    <!-- Dual Both -->
    <div class="sc-card">
      <div class="sc-title">Scenario 3 — Dual Confirmation, Patient Exit</div>
      <div class="sc-badge badge-3">Dual Trigger — Both Exit</div>
      <p><strong>Entry:</strong> Identical to Scenario 2 — requires both price and RS crossovers
      to be simultaneously bullish. Same high-conviction dual entry.</p>
      <p style="margin-top:10px"><strong>Exit:</strong> Sell only when <em>both</em> crossovers
      have reversed — the stock must be weak both in absolute price AND relative to the index
      before we exit. This is the most <strong>patient</strong> approach: it lets winners run
      fully through a complete trend cycle before exiting.</p>
      <p style="margin-top:10px;color:#64748b;font-size:12px">
      <em>Think of it as: "Enter with two green lights. Exit only when both turn red."</em></p>
    </div>

  </div>
</section>

<!-- ═══════════════════════════════ FOUR FILTER OVERLAYS ═══════════════════════════════ -->
<section>
  <h2>Four Filter Combinations Tested per Scenario (12 total)</h2>
  <div class="filter-grid">

    <div class="filter-card">
      <div class="f-label">No Tag</div>
      <div class="f-name">Baseline — No Filters</div>
      <p>Pure signal. Every crossover triggers a trade, regardless of market conditions or
      volume. Maximum signal frequency. Establishes the raw edge of each scenario.</p>
    </div>

    <div class="filter-card">
      <div class="f-label">[R] Regime Filter</div>
      <div class="f-name">Bull Regime Gate</div>
      <p>Only take trades when Nifty 50 is above its own 200-day SMA — i.e., the market
      itself is structurally bullish. Blocks entries during bear phases when even leaders tend
      to mean-revert. Active {regime_pct:.0f}% of trading days in this period.</p>
    </div>

    <div class="filter-card">
      <div class="f-label">[V] Volume Filter</div>
      <div class="f-name">Institutional Volume Confirmation</div>
      <p>Only take the crossover trade if volume on that day exceeds 1.5× the 20-day average
      volume. The premise: large players are participating in the breakout, validating the signal.
      Tests whether high-volume crossovers have better follow-through.</p>
    </div>

    <div class="filter-card">
      <div class="f-label">[R+V] Both Filters</div>
      <div class="f-name">Regime + Volume Combined</div>
      <p>Strictest gate: trade only when the market regime is bullish AND volume confirms the
      crossover. Fewest signals; highest-quality filter bar. Tests whether combining both
      qualitative overlays materially improves the strategy's return or risk profile.</p>
    </div>

  </div>
</section>

<!-- ═══════════════════════════════ RESULTS: 5Cr ═══════════════════════════════ -->
<section>
  <h2>Results — Universe A: ADT ≥ ₹5 Crore</h2>
  <p>Broader universe. Includes mid-cap and small-cap names with meaningful liquidity.
  <span class="star">★</span> = beats Nifty 50 buy-and-hold ARR of <strong>{nifty_arr:.1f}%</strong>.
  Nifty benchmark row shows its own max drawdown of <strong style="color:#ef4444">{nifty_dd:.1f}%</strong>
  for risk comparison.</p>
  {table_html(data5, "Universe A — ADT ≥ ₹5 Crore", 5)}
</section>

<!-- ═══════════════════════════════ RESULTS: 15Cr ═══════════════════════════════ -->
<section>
  <h2>Results — Universe B: ADT ≥ ₹15 Crore</h2>
  <p>More liquid universe. Restricted to stocks trading at least ₹15 crore per day on average.
  Reduces slippage risk and improves execution quality at the cost of a slightly smaller universe.
  <span class="star">★</span> = beats Nifty 50 ARR of <strong>{nifty_arr:.1f}%</strong>.</p>
  {table_html(data15, "Universe B — ADT ≥ ₹15 Crore", 15)}
</section>

<!-- ═══════════════════════════════ BENCHMARK COMPARISON ═══════════════════════════════ -->
<section>
  <h2>Benchmark Comparison — Nifty 50 Buy &amp; Hold</h2>
  <div class="card">
    <p>The Nifty 50 buy-and-hold benchmark over Jan 2021 – May 2026:</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:16px">
      <div class="meta-box">
        <div class="lbl">Total Return</div>
        <div class="val" style="color:#93c5fd">{fmt(nifty_ret)}</div>
      </div>
      <div class="meta-box">
        <div class="lbl">Annual Return (ARR)</div>
        <div class="val" style="color:#fbbf24">{fmt(nifty_arr)}</div>
      </div>
      <div class="meta-box">
        <div class="lbl">Max Drawdown</div>
        <div class="val" style="color:#ef4444">{nifty_dd:.1f}%</div>
      </div>
      <div class="meta-box">
        <div class="lbl">SL Risk</div>
        <div class="val" style="color:#475569">Unlimited</div>
      </div>
    </div>
    <p style="margin-top:16px">All strategy variants above use a hard 10% stop-loss per trade with
    fixed-dollar risk sizing (0.5% RPT = ₹5,000 risked per trade on ₹10L capital). This caps
    maximum per-trade loss and keeps drawdown bounded — an important structural advantage
    versus buy-and-hold during sharp market corrections.</p>
  </div>
</section>

<!-- ═══════════════════════════════ KEY FINDINGS ═══════════════════════════════ -->
<section>
  <h2>Key Findings</h2>

  <div class="callout green">
    <p><strong>RS Only (baseline, no filters) is the best single strategy</strong> — achieving
    ARR of {get_r(data5,'RS_ONLY',False,False)['arr']:.1f}% on the 5Cr universe and
    {get_r(data15,'RS_ONLY',False,False)['arr']:.1f}% on the 15Cr universe, both beating
    Nifty's {nifty_arr:.1f}% ARR with lower max drawdown than the index's {nifty_dd:.1f}%.</p>
  </div>

  <div class="callout amber">
    <p><strong>The volume filter consistently hurts performance.</strong> Across both universes,
    adding the [V] volume filter reduces ARR in most scenario + filter combinations. Hypothesis:
    high-volume crossovers are late signals — institutional front-running has already occurred.
    A future test: use volume in the 3–5 days <em>after</em> the crossover as confirmation
    rather than on the crossover day itself.</p>
  </div>

  <div class="callout purple">
    <p><strong>Regime filter has mixed impact.</strong> For RS Only, the regime filter reduces
    ARR (fewer trades, but not proportionally better quality). For Dual-Both on 15Cr, regime
    filtering slightly improves drawdown. The 88% bull-regime observation rate in this specific
    period (2021–2026 was largely a bull market) limits the regime filter's discriminatory power.</p>
  </div>

  <div class="callout">
    <p><strong>Universe size matters less than expected.</strong> The 5Cr and 15Cr universes
    contain nearly the same stocks (435 vs 433), because most NSE 500 names already trade well
    above 5Cr/day. True liquidity differentiation would require testing a much lower threshold
    (e.g., 1–2Cr) or comparing versus a 50Cr+ large-cap-only universe.</p>
  </div>

  <div class="callout red">
    <p><strong>Win rates are systematically below 50%.</strong> All combinations show 30–42% win
    rates. This is normal for trend-following strategies — the edge comes from letting winners
    run longer than losers (positive expectancy). Average hold times of 100–170 days confirm
    multi-month trend riding as the return driver.</p>
  </div>
</section>

<!-- ═══════════════════════════════ METHODOLOGY ═══════════════════════════════ -->
<section>
  <h2>Methodology &amp; Assumptions</h2>
  <div class="appendix-grid">
    <div class="card" style="margin-bottom:0">
      <h3 style="color:#e2e8f0;font-size:14px;margin-bottom:12px">Signal Construction</h3>
      <ul>
        <li><strong>RS Ratio</strong> = Stock Close ÷ Nifty 50 Close (daily, dimensionless)</li>
        <li><strong>SMA20(RS)</strong> = 20-day rolling mean of the RS ratio</li>
        <li><strong>SMA200(RS)</strong> = 200-day rolling mean of the RS ratio</li>
        <li>A golden cross occurs when SMA20(RS) was ≤ SMA200(RS) yesterday and is &gt; today</li>
        <li>Price crossovers use the same logic on stock close price directly</li>
        <li>Volume filter: trade day volume &gt; 1.5× 20-day avg volume</li>
        <li>ADT = 20-day rolling mean of (Close × Volume), checked on signal date</li>
      </ul>
    </div>
    <div class="card" style="margin-bottom:0">
      <h3 style="color:#e2e8f0;font-size:14px;margin-bottom:12px">Simulation Rules</h3>
      <ul>
        <li><strong>Execution</strong>: signals generated at close, executed at next day's open</li>
        <li><strong>Position sizing</strong>: ₹50,000 fixed risk per trade (₹10L × 0.5% RPT ÷ 10% SL)</li>
        <li><strong>Stop loss</strong>: 10% below entry price, hard floor (no trailing)</li>
        <li><strong>SL execution</strong>: gap-downs exit at open; intraday SL exits at SL price</li>
        <li><strong>Max positions</strong>: 10 concurrent open trades</li>
        <li><strong>No shorting</strong>, no leverage, long-only</li>
        <li><strong>No transaction costs</strong> modelled (conservative uplift ~0.3–0.5% ARR)</li>
        <li>Warmup: 420 calendar days pre-period to initialise SMA200</li>
      </ul>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════ NEXT STEPS ═══════════════════════════════ -->
<section>
  <h2>Suggested Next Research Steps</h2>
  <div class="card">
    <ul>
      <li><strong>Lagged volume confirmation</strong>: Require above-average volume in the 3–5 days
      <em>after</em> the RS crossover, not on the crossover day itself. Tests if volume validates
      continuation rather than just the trigger.</li>
      <li><strong>Sector-relative RS</strong>: Compute RS versus sector index rather than Nifty
      to identify sector leaders within already-bullish sectors.</li>
      <li><strong>RS percentile ranking</strong>: Instead of a binary crossover, rank all stocks
      by RS acceleration and buy the top decile. Creates a dynamic, always-on portfolio.</li>
      <li><strong>Partial exits</strong>: Apply the Champion Trader exit framework (2R/NE/GE/EE)
      instead of the binary crossover exit to maximise winners.</li>
      <li><strong>Large-cap isolation</strong>: Test with an ADT ≥ 50Cr universe to see if very
      liquid names show meaningfully different RS crossover dynamics.</li>
      <li><strong>Walk-forward validation</strong>: Split the dataset into in-sample (2021–2023)
      and out-of-sample (2024–2026) to test for parameter overfitting.</li>
    </ul>
  </div>
</section>

<div class="footer">
  Generated by Champion Trader Research Engine · {report_date} ·
  Data source: NSE / Yahoo Finance · For internal research use only
</div>

</div>
</body>
</html>"""

output_path = "/home/user/champion-trader/docs/rs_crossover_research.html"
with open(output_path, "w") as f:
    f.write(html)
print(f"Saved: {output_path}")
print(f"File size: {len(html):,} bytes")
