# Champion Trader System — Deep Analysis & Personal-System Roadmap

_Author: engineering analysis pass. Goal: turn the existing CTS into a personal,
comprehensible swing-trading system (risk management, position sizing, simulation,
backtest, "simple thought processes") wired to a Zerodha account, paper-first._

> **Reading guide.** Section 1 is the honest diagnosis. Section 2 is the part you
> specifically asked for — the **logic shifts** (conceptual changes, not just bug
> fixes). Section 3 is the **phased build plan**. Section 4 is the **quick-win bug
> list** with file:line. Section 5 is **decisions needed from you**.

---

## 0. One-paragraph verdict

The **trading core is real and mostly correct**: position sizing is exact and
tested, the risk-guardian (trailing stops, open-risk and drawdown freezes) has
good bones, and the raw candle math (TRP, close-position, volume-ratio, single-bar
PPC/NPC) faithfully matches the methodology. The problem is everything _around_ that
core. The "intelligence/learning" layer is **largely decorative and statistically
unsound** — it overfits a tiny in-sample window nightly, its "AI" is mostly if/else
templates, and its smartest components (setup scoring, regime tuning, attribution)
**don't actually feed live trades**. The candle _interpretation_ layer (base, stage,
READY/NEAR/AWAY, sector strength) **diverges from your own README**. The backtest is
**systematically optimistic** (no costs, no slippage, stops that magically fill at the
stop on gap-downs). And there is **no real broker or live-data feed** — "live" prices
are delayed yfinance, and only stop-loss SELLs ever touch the (paper) broker. None of
this is fatal. The bones are good; the work is to **simplify, make honest, and wire
the seams that already exist.**

---

## 1. Diagnosis

### 1.1 System map (as actually built)

- **Backend**: FastAPI + SQLite (SQLAlchemy), 21 tables, ~11.5k LOC. `Decimal` for money.
- **Frontend**: Next.js 14 App Router, ~11 real pages + several legacy redirects. Settings (account value, RPT, stance) live in browser `localStorage`.
- **Data**: `yfinance` only — NIFTY-200 universe, **daily bars**, 9 months history. No intraday, no broker feed.
- **Scheduler**: 12 APScheduler jobs in IST (scan 16:00, regime 16:45, CIO 17:00, corpus 17:30, autooptimize 18:00–08:00, exit-monitor every 2 min, entry-monitor every 1 min 15:00–15:30, risk-guardian every 10 min, learning every 30 min, shadow every 30 min).
- **Broker**: one clean ABC (`BaseBrokerClient`, 6 methods) + a working `PaperBrokerClient` + stub `Jhaveri`/`Dhan`. Used in exactly **one** place — autonomous SL SELL.
- **Two disconnected pipelines**: (a) the **backtest** engine (daily-bar replay) and (b) the **live/paper** path (yfinance snapshots → `ActionAlert` → DB `Trade`). They share **no signal code**.

### 1.2 What is genuinely solid (keep, protect with tests)

| Area | File | Status |
|---|---|---|
| Position sizing | `backend/services/position_calculator.py` | Exact `Decimal` math; matches ASTERDM/MARICO/SWARAJENG. |
| Methodology constants | `backend/services/trading_rules.py` | Faithful to README §12. |
| Risk guardian logic | `backend/intelligence/risk_guardian_checks.py` | Trailing (BE→2R→LOD), open-risk >10%, month-DD >6% freeze, sector concentration. |
| Portfolio math | `backend/intelligence/portfolio_math.py` | Real numpy VaR / drawdown / correlation / open-risk. |
| Raw candle math | `backend/services/technical.py` (`calculate_trp`, `close_position`, vol ratio) | Correct; matches README & Pine. |
| Backtest exit ladder + trailing | `backend/services/backtest_engine.py` | Most methodology-faithful module (2R/NE/GE/EE %, SL progression, 50/20-DMA final exit). |
| Broker seam | `backend/intelligence/broker_client.py` | Clean ABC + factory — Zerodha is one new class. |
| Telegram | `backend/services/notifications.py` | Functional (one arg-count bug, §4). |

### 1.3 Problem clusters

**P1 — The "learning" layer is decorative and overfits.**
- `results.tsv` (the optimizer's experiment log) is **empty** — header only. Whatever ran left no durable learning.
- AutoOptimize is greedy hill-climbing: changes **one parameter at a time**, accepts on a bare `new_score > baseline_score` with **no train/test split, no significance test, minimum 8 trades**, over a single fixed ~60-trading-day window. This is an in-sample memorizer, not a learner. (`autooptimize.py:126`, `autooptimize_scoring.py:38,63`)
- "Hypotheses" are `random.uniform` nudges, not reasoning (`autooptimize_proposals.py:280-287`).
- The only real Claude call (`autooptimize_analysis.py`) has its output **logged and discarded** — it never feeds the next hypothesis.
- The "Claude learning note" (`learning_agent.py:269`) and "Claude recommendation" (`cio_agent.py:260`) are **if/else templates**, not LLM calls.
- **The smart parts don't reach live trades.** The composite setup-scorer (`signal_agent.py`) and the regime-specific parameter banks (`parameter_banks.py`) feed **only** the CIO brief and the API display. The live scanner uses raw `PARAMETERS` thresholds and never imports them. So regime tuning and quality scoring change what's _printed_, not what's _traded_.
- `signal_attribution` is **written but read by nothing** — the underperformance flags go nowhere.
- Dead/empty inputs: `corpus_a` (methodology "bible") is **never populated**; regime silently defaults to `RANGING_QUIET` on any data hiccup; the CIO recommendation branches on regime strings (`BULLISH/BEARISH/CRISIS`) the classifier **never emits** (`cio_agent.py:272,278` vs `regime_classifier.py`).

**P2 — The candle _interpretation_ layer diverges from your methodology.**
- **READY/NEAR/AWAY uses the wrong definition.** README: READY = "contraction + trigger bar identified." Code: READY = "Stage 1B/2 + ≥20 base days + decent quality," with `trigger_level` not even a precondition (`scanner_engine.py:82-88`). The single most important output is computed against the wrong rule.
- **Stage bands overlap and are order-dependent** — a _topping_ stock can be tagged `S1B` (a buy bucket) (`technical.py:108-133`). The README's "higher highs" gate for Stage 2 is dropped.
- **Contraction is the weakest signal.** The "narrowing" counter accepts candles **up to 5% _wider_** than the prior bar (inverted tolerance), so it doesn't actually require contraction; ATR "slope" is a 2-point ratio, not a slope (`technical.py:208-243`).
- **Sector strength is entirely absent.** No sector column on `ScanResult`, no sector map in `nse_stocks.py`, no PPC-vs-NPC aggregation. Market Stance is **manual typed input** despite the README defining the algorithm. NPC's stated purpose ("find weak sectors") is unwired.
- **WUC + 6 of 7 base features are faked** — `wuc_type` is a hardcoded constant per scan type (`"MBB"` for PPC, `"BA"` for contraction).
- **`min_trp > 2` tradeability gate is never enforced** anywhere, though it's a "non-negotiable" rule.
- **Optimizer knobs aren't wired** — `contraction_atr_lookback` (and the narrowing lookback) are tuned by the optimizer but **ignored** by the scanner (hardcoded `slope_bars=5`).
- **Daily-only**: the README's multi-timeframe "WTF" (weekly stage + daily base + 60-min entry) is ~⅓ implemented. No 60-min entry logic exists.
- **Pine ≠ Python** for contraction and stage — a TradingView flag and a backend flag won't reliably be the same stock.

**P3 — The backtest is systematically optimistic, and sim ≠ live.**
- **No transaction costs anywhere** — zero brokerage/STT/slippage. For a strategy that takes **four partial exits per winner**, Indian round-trip costs are first-order and would visibly erode the edge.
- **Asymmetric optimistic fills** — entries fill at the exact trigger even on gap-ups; **stops fill exactly at the stop even on gap-downs** (understates losses). This inflates win rate, R-multiples, and expectancy.
- **Daily-bar intrabar ambiguity** — it can't know whether the low or the high came first, so SL-vs-target ordering is guessed; multiple targets can book in one bar.
- **Survivorship bias** — replays history over _today's_ NIFTY constituents.
- **Backtest signal code ≠ live scanner code** (`backtest_strategies.py` vs `technical.py`), so backtest results don't provably predict production.
- **Paper path is weaker still** — no trailing stops, and it books forced/final exits at the **entry price** (a zero-P&L placeholder) (`paper_trading.py:195-196`).

**P4 — No live data feed and no live execution (the Zerodha gap).**
- "Live" prices are **delayed yfinance** (`fast_info.last_price` / `info["regularMarketPrice"]`, ~15-min delay) across **four scattered fetchers**. That is wrong for the last-30-minute trigger-break logic the whole method depends on.
- **Only SELL (stop-loss) ever touches the broker**; BUY entries are pure DB writes in both the human and autopilot paths. There's no live order placement, no Kite auth/daily-token model, no websocket, no order/position reconciliation.

**P5 — Account value has no single source of truth.**
- The backend risk layer reads a **static `settings.default_account_value`** from `.env`; the frontend keeps a **separate** copy in `localStorage`. Neither is tied to a real balance. Risk math and the 10% open-risk cap are computed against a number that can silently be wrong.

**P6 — Comprehensibility.**
- You asked for a system you _understand_. Today the surface area is huge (RAG with 3 corpora, CIO agent, 4-file optimizer, shadow portfolio, baseline A/B, regime banks, signal scorer) and much of it is theater that's disconnected from the trades that actually happen. Complexity without payoff is the enemy of "I can take calls based on this."

---

## 2. Logic shifts (the conceptual changes)

These are the _re-framings_ that turn this from "an autonomous-AI-hedge-fund cosplay"
into "a transparent personal decision system."

**Shift 1 — From a fake AI brain to a transparent rule engine + honest journal.**
The value of a personal system is that every recommendation is **explainable on one
screen**: _"ASTERDM is READY because Stage 2 ✓, 24-bar base ✓, contraction over last 4
bars ✓, trigger 1,240, TRP 3.1% → size 65+65, risk ₹2,500 = 0.5% of capital."_ Replace
the opaque "intelligence" with a **decision card** (why it qualified, which rules
passed/failed) and a **post-trade journal** (honest, real attribution). "Learning" you
can read beats a black box you can't.

**Shift 2 — Redefine READY/NEAR/AWAY to match the methodology.** READY must mean
"contraction tightening + trigger bar identified + alert armed at trigger level," not
"Stage 2 + 20 base days." This is the difference between a watchlist that tells you
_what to do tomorrow_ and one that just labels maturity.

**Shift 3 — One signal path. Backtest == live == paper.** Delete the duplicate
backtest signal functions and have the backtest call the **same** `technical.py` /
scanner code the live system uses. One price-provider interface, one account-value
source of truth, one definition of a "signal." If they can't diverge, the backtest
actually predicts production.

**Shift 4 — Make the backtest honest before trusting a single number.** Add a cost
model (brokerage + STT + stamp + exchange + GST) on **every** leg, a slippage model,
**pessimistic fills** (enter at `max(trigger, day_open)`, stop at `min(stop, day_open)`,
assume stop-before-target on ambiguous bars), and a **point-in-time universe**. Report
after-cost expectancy _with trade counts and confidence_, not a hero number.

**Shift 5 — Learning that's slow, validated, and actually fed back.** Personal swing
trading produces ~5–20 trades/month — you **cannot** learn parameters nightly from that
without fitting noise. Replace 168-experiments/night hill-climbing with: (a) a
**walk-forward harness** (optimize on window A, _only_ keep parameters that also improve
out-of-sample window B, with a minimum-trade and significance gate); (b) **real
per-(signal × regime × sector) attribution** that the ranker actually reads; (c)
**recalibrate quarterly**, not nightly; (d) a qualitative **journal** that surfaces
_your_ recurring mistakes. Honest and infrequent beats fast and fake.

**Shift 6 — Compute market stance, don't type it.** Add a sector map, aggregate
PPC-vs-NPC per sector each evening, and derive STRONG/MODERATE/WEAK + the RPT% and
max-position adjustments automatically. This closes the loop the README designed.

**Shift 7 — Zerodha is the backbone, introduced paper-first.** Kite Connect provides
both the **real intraday quote feed** (KiteTicker websocket) and **execution** — so the
data-feed fix and the broker migration are _the same project_. Gate everything behind
`broker_live_trading=false` and run 10–15 days of paper validation with the real feed
before a single rupee is live.

---

## 3. Phased build plan

Each phase is independently useful and leaves the system in a working state.

**Phase 0 — Quick-win correctness (days).** Fix the silent bugs in §4. These are cheap,
high-value, and several (Telegram arg-count, `min_trp` gate, contraction tolerance,
account-value source) directly affect safety. _Deliverable: the system stops lying to
itself._

**Phase 1 — Candle/scanner fidelity.** Realign READY/NEAR/AWAY to contraction+trigger;
fix stage band overlaps + restore the higher-highs/volume gates; replace the base
heuristic with genuine support/resistance + structure detection; add a sector map and
**computed** market stance; wire the ignored optimizer knobs; enforce `min_trp`. Unify
the backtest onto `technical.py`. _Deliverable: scans that match your methodology and a
backtest that uses the same signals as live._

**Phase 2 — Honest simulation.** Cost + slippage + pessimistic-fill model; point-in-time
universe; bring the trailing/DMA exit logic into the paper path; remove the
entry==trigger and final-exit==entry fudges. _Deliverable: backtest/paper numbers you
can size real money on._

**Phase 3 — Transparent decision layer ("simple thought processes").** Per-setup
**explainability card**; a **decision/trade journal** with real post-mortems; **strip or
quarantine** the decorative AI (CIO agent, RAG, shadow portfolio, nightly optimizer) so
the surface area matches what actually drives decisions. _Deliverable: a system you can
read end-to-end in an afternoon._

**Phase 4 — Honest learning loop.** Walk-forward validation harness; attribution that
feeds the ranker; quarterly recalibration; weekly review surfacing your patterns.
_Deliverable: parameters that generalize, and a journal that makes you better._

**Phase 5 — Zerodha integration (paper-first).** `KiteBrokerClient(BaseBrokerClient)`
for orders; **KiteTicker** websocket price provider behind a single `PriceProvider`
interface (replaces all 4 yfinance fetchers in the hot path); daily token-refresh job +
login/callback endpoint + persisted session; live **BUY** path with the 50/50 split and
freeze/risk gating; **order/position reconciliation** (postback endpoint + boot-time
sync); **account value synced from `kite.margins()`**. All gated by
`broker_live_trading`. _Deliverable: real quotes + (optional) real execution, paper by
default._

**Phase 6 — Go-live discipline.** 10–15 trading days of paper with the live feed; review
after-cost expectancy and journal; then **small-size** live with all guards on
(freeze, 10% open-risk cap, SL autonomy). _Deliverable: a controlled transition to real
capital._

---

## 4. Quick-win bug list (Phase 0)

| # | Bug | Location | Impact |
|---|---|---|---|
| 1 | `send_alert(message)` calls `send_telegram_alert(message)` but signature is `(alert_type, message)` → `TypeError` swallowed | `risk_guardian_checks.py` (`send_alert`) | **SL / risk Telegram alerts are silently never delivered.** |
| 2 | `min_trp > 2` tradeability gate not enforced in any scan | `scanner_engine.py` | Illiquid/untradeable stocks pass as signals. |
| 3 | Contraction "narrowing" accepts candles up to 5% _wider_ (inverted tolerance) | `technical.py:236-243` | Contraction scan flags non-contracting stocks. |
| 4 | CIO recommendation branches on regime strings the classifier never emits | `cio_agent.py:272,278` | Regime-aware advice is unreachable. |
| 5 | Optimizer tunes `contraction_atr_lookback` / narrowing lookback the scanner ignores | `scanner_engine.py:222-223` | Optimization effort produces no behavioral change. |
| 6 | Account value read statically from `.env`, separate copy in frontend `localStorage` | `risk_guardian_checks.py`, `routers/intelligence.py:281`, `settings-context.tsx` | Risk math computed against a possibly-wrong number. |
| 7 | `wuc_type` hardcoded per scan type (`"MBB"`/`"BA"`) | `scanner_engine.py:129,228` | Base-feature tags carry zero information. |
| 8 | Regime silently defaults to `RANGING_QUIET` / VIX `15.0` on any data error | `regime_classifier.py:136,151` | Data outages masquerade as a real classification. |
| 9 | `corpus_a` (methodology memory) never ingested | `rag_engine.py` / no caller | One-third of "memory" is permanently empty. |
| 10 | NPC stocks pushed through long-only READY/NEAR bucketing | `scanner_engine.py:185-187` | Bearish signals get nonsensical buy buckets. |

---

## 5. Decisions needed from you

1. **The "intelligence" layer** — simplify to an honest core (recommended), fully fix &
   wire it, or leave it untouched and focus on the trading core?
2. **Live data + execution** — commit to Kite Connect now (it's the only realistic source
   of live NSE intraday quotes _and_ execution), or stay paper-first on yfinance and wire
   Kite later? Note: Kite Connect needs a paid monthly subscription + app registration +
   a daily login/token step.
3. **Where to start** — quick-win bug fixes, candle/scanner correctness + honest backtest,
   or Zerodha integration first?

---

_This is a living plan. Nothing here is committed in stone; it's the map for turning a
broad, half-wired platform into a tight, honest, personal trading system._
