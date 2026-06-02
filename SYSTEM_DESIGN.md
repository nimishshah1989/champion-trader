# How the Champion Trader System Will Work — operating synopsis

Plain-English description of the system we're building: what it does, how it runs day
to day, and the life of a single trade. Companion to `REWIRE_PLAN.md` (the technical
build plan) and `STRATEGY_CARD.md` (the strategy spec). Read this to understand the
*operating model* before any code is written.

---

## 1. In one paragraph

A fully-automated swing-trading system that runs the **validated v2 strategy** on liquid
NSE stocks (≥ ₹5cr/day turnover) through **Zerodha/Kite**. After each market close it
scans the universe for v2 breakout setups and builds tomorrow's watchlist. In the **last
30 minutes** of the next session it enters the names that break their trigger on
confirming volume. It then manages every open position with a **close-based 5×ATR
trailing stop** — riding winners, cutting losers only on a confirmed close below the
stop — with sizing and portfolio risk governed by **fixed rules** (risk 0.35% per trade,
max 15 positions, quarter-size in bear regimes, halt on a 15% drawdown). You supervise
from a **dashboard and Telegram**, in either fully-automatic or approve-each-action mode.
**Phase 1 runs on paper** (no real money); **Phase 2 places real orders** via Kite.

---

## 2. One brain, many hands

The validated v2 logic lives in **one place** — `backend/engine/runtime/`:

| module | answers | output |
|---|---|---|
| `signal_service` | "Is this stock a v2 entry today?" | trigger price + stop distance, or nothing |
| `exit_service` | "What do I do with this open position on today's bar?" | hold (ratchet the trail) or exit |
| `risk_manager` | "How many shares, and am I allowed to take it?" | size, after caps/bear-sizing/DD checks |

**Everything else calls this brain** — the scanner, the entry/exit monitors, the
autopilot, the alerts. There is no second strategy anymore. (Already proven: the runtime
reproduces the backtest **trade-for-trade, 293/293**.)

---

## 3. A day in the life of the system (IST)

The system's real "moment" each day is the **last 30 minutes** — that's when both
entries and exits actually execute, the way a real swing trader runs it ("review at EOD,
act near the close"). Everything else is preparation.

| time | what happens | which job |
|---|---|---|
| **09:15** | **Morning gap-check.** Any open position that *gaps open below* its trailing stop is exited at the open (overnight gap risk). | exit_monitor (open) |
| 09:15–15:00 | Idle for decisions (v2 acts on the close, not intraday wiggles). Optional non-binding watch only. | — |
| **15:00–15:30** | **THE ACTION WINDOW.** ① **Entries:** each READY watchlist name trading above its trigger on ≥2× volume → `risk_manager` sizes it → BUY near the close. ② **Exits:** any open position trading below its trail → SELL near the close (a confirmed close-below). | entry_monitor + exit_monitor |
| 15:30 | Market close. | — |
| **~15:45** | **Data ingest.** Pull the day's Kite-adjusted OHLCV for the universe + NIFTY 500 into the database. | ingest (repurposed corpus_updater) |
| **16:00** | **Exit bookkeeping + scan.** ① Ratchet every open trail up: `stop = max(old, highest_high − 5×ATR)`. ② Run `signal_service` across the ≥5cr universe → write today's v2 setups → refresh the **READY/NEAR watchlist for tomorrow**. | daily_scanner |
| **16:45** | **Regime check.** Is NIFTY 500 above its rising 50-DMA? Sets tomorrow's bear-sizing flag (full size vs 0.25×). | regime_classifier |
| **17:00** | **Daily brief to Telegram:** new setups, tomorrow's watchlist, open positions + their current trails, today's exits, portfolio equity / open risk / drawdown. | cio_agent |
| overnight | Nothing. (AutoOptimize is frozen — thresholds don't auto-change.) | — |
| weekly | Journal / self-review entry (existing weekly journal). | — |

> **Why this is simpler than the old system:** because v2 is close-based, the system does
> **not** need to watch open positions tick-by-tick (the old 2-min polling that caused
> premature exits). It needs one decision near the close + one morning gap-check. Less
> infrastructure, and it matches the methodology.

---

## 4. The life of a single trade

1. **Spotted** (Day D, after close): stock X passes the v2 scan — Stage 2 uptrend,
   volatility contraction, valid base, avg TRP ≥ 2 — and lands on the watchlist as
   **READY**, with a trigger price *T* (the 5-day high) and a stop distance.
2. **Entered** (Day D+n, last 30 min): X trades above *T* on **≥2× its average volume**
   → `risk_manager` computes size = (0.35% of equity) ÷ stop-distance, scaled to **0.25×**
   if the market's in a bear regime, **skipped** if we already hold 15 positions or a 15%
   drawdown halt is active or it's circuit-locked → **BUY** near the close. Initial stop =
   **entry − 1×TRP**.
3. **Managed** (every day after, at the close): the trail ratchets up — `stop = max(old,
   highest_high − 5×ATR)`. There is **no profit target**; the position rides.
4. **Exited:** the first day X **closes below the trail** (or **gaps below at the open**)
   → **SELL the whole position.** The R-multiple and P&L are recorded, Telegram notifies,
   the journal updates.

That's the whole loop. ~73% of trades exit for a small loss (~−1R); the minority that
trend pay for them many times over. **You must take every signal** — the winners are
unpredictable and a handful make the year.

---

## 5. The safeguards (always on)

- **Per-trade risk:** 0.35% of equity. **Max 15 concurrent positions.**
- **Bear-sizing:** quarter-size new entries when NIFTY 500 is below its rising 50-DMA.
- **Drawdown circuit-breaker:** at −15% from the equity peak, **halt new entries** (open
  positions keep running); resume when back within 7.5%.
- **Liquidity floor:** only trade names ≥ ₹5cr/day turnover (configurable; ≥ ₹15cr for
  large capital) — the fillable, less survivorship-prone universe.
- **Kill-switch** (Phase 2): one control to stop all new orders immediately.

---

## 6. What you see and do

- **Dashboard** (the existing Next.js app): watchlist, open positions with their live
  trailing stops, pending BUY/SELL actions, trade history, equity curve, portfolio risk.
- **Telegram:** entry signals, exit signals, the daily brief, risk warnings.
- **Two modes:**
  - **APPROVE** — the system proposes each BUY/SELL; you tap to confirm. (Recommended for
    early paper trading, to build trust.)
  - **AUTO** — the system executes on its own within the rules. (The end state.)

---

## 7. Data & broker — one provider

**Zerodha/Kite** supplies *both* the adjusted historical bars the brain reasons on *and*
the order execution. One login, one session, and — crucially — **the live data feed is
identical to the backtest feed**, which removes the price-adjustment mismatch that caused
the original phantom-loss bug. (The old yfinance scan feed and the Dhan stubs are retired.)

---

## 8. The honest expectations (what to plan around)

- **~16–18% deployable CAGR** (ex-2021), **not** the 26.5% headline — that figure leaned on
  sub-₹1cr micro-caps you can't fill at size and on the one-off 2021 melt-up.
- **Win rate ~35%**, win/loss magnitude ~8:1. Long stretches of small losses between trends.
- **Flat years happen** (2018, 2022 were ~0 across all tiers). The recent liquid-tier boom
  (2023–26) is real but must not be extrapolated either.
- **Drawdowns to ~15–17%** are normal and expected; the circuit-breaker caps the tail.

---

## 9. What gets built, in order (maps to REWIRE_PLAN.md)

- **Phase 0 — Foundation.** ✅ `signal_service` + `exit_service` extracted & parity-proven
  (293/293). Remaining: `risk_manager` extraction + portfolio parity; trailing-stop DB
  column; Kite adjusted-bar ingest.
- **Phase 1 — Paper on the validated engine.** Wire scan → watchlist → last-30-min entry →
  sizing → close-based exit → trades/journal → Telegram, all calling the runtime. Run in
  **shadow** alongside the legacy path first, then **paper** for 10–15 sessions; reconcile
  real fills vs the backtest. **No real money.**
- **Phase 2 — Live on Kite.** Real orders behind the same runtime, ≥₹15cr tier if capital
  is large, hard risk gates + kill-switch + daily broker reconciliation.

---

*The validated strategy is fixed and proven; this system is the disciplined machine that
executes it without emotion, takes every signal, and never widens a stop.*
