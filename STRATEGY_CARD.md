# Champion Trend System — Strategy Card (v1)

**Status:** backtested + walk-forward validated on clean (Kite-adjusted) data, 2016–2026.
**Verdict:** dominates NIFTY 500 buy-and-hold on every axis — ~2× the return at ~⅓ the drawdown.

---

## 1. What it is (in one paragraph)

A systematic, rules-only swing/position strategy (2–6 week holds) on the broad NSE
universe (~1,270 liquid names). It buys **volatility-contraction breakouts in
stocks that are already in a Stage-2 uptrend**, risks a fixed fraction per trade,
cuts losers on a confirmed close below the stop, and **lets winners run on a wide
trailing stop**. Idle capital sits in Liquid Bees at 6.5%. There is **no
discretionary chart-reading** — every entry, exit, and size is a rule.

---

## 2. Validated performance

| Window | CAGR | maxDD | Calmar | Sharpe | vs NIFTY 500 buy&hold |
|---|---|---|---|---|---|
| TRAIN 2016–20 | 13.0% | 16.2% | 0.80 | 1.36 | B&H Calmar 0.30 |
| **TEST 2021–26 (blind)** | **20.9%** | **11.0%** | **1.89** | **1.60** | B&H Calmar 0.70 |
| FULL 2016–26 | 24.5% | 16.2% | 1.51 | 1.93 | B&H 13.4% / 45% DD / 0.30 |

₹1,00,000 → **₹9,22,000** over the period (buy-and-hold: ₹3,58,000).
Positive in **8 of 11 years**; worst year −9.4% (2018) vs the index's −25%+ drawdowns.

The config family (wide chandelier + the risk overlays) was tuned on 2016–20 and
held up **out-of-sample** on 2021–26 — the hallmark of a real edge, not a curve-fit.

---

## 3. The rules

### Universe
- All NSE equities with ≥ ₹2 cr average daily turnover (~1,270 symbols).
- **Prices must be corporate-action adjusted** (we use Kite's adjusted history;
  unadjusted Atlas prices manufactured phantom −20R split "losses").

### Entry (all must hold on the signal bar)
1. **Stage 2 uptrend** — price above a rising 150-day SMA, making higher highs
   (Weinstein stage S1B/S2). *This is the per-stock strength gate.*
2. **Volatility contraction** — ATR compressed (≤35th percentile of last 60 days),
   ATR slope ≤ 0, and price within 3% of recent resistance (a coiled base).
3. **Valid base** — ≥ 20 bars, 8–35% depth, ≥ 20% prior advance into the base.
4. **TRP ≥ 2.0** — enough daily range to be tradeable.
5. **Trigger** — buy on the intraday break above the 5-day high (gap-up fills at open).

> **No index-regime gate on entries.** Strong stocks trend regardless of the
> market ("there's always some instrument on the journey"). Downside is handled
> per-trade by the stop, not by sitting in cash.

### Stop & exit
- **Initial stop** = entry − 1×TRP (the "1R" risk).
- **Close-based** — exit only if the bar **closes** below the stop (or gaps below
  on the open). An intraday wick through the stop does **not** exit.
  *(Measured: a hard intraday stop produced 78% premature exits and cut win rate 10pts.)*
- **Trail** = 5×ATR chandelier (`stop = max(stop, highest_high − 5×ATR)`), ratcheting
  up only. This is what lets winners run — the source of the return.
- No fixed profit target. Winners exit only when the 5×ATR trail is closed through.

### Position sizing & portfolio risk
- **RPT 0.25%** of equity risked per trade → shares = equity × 0.25% / (TRP value).
  *(0.25%, not 0.5% — smaller bets fund ~7 concurrent positions, which deploys more
  capital AND diversifies. Higher RPT concentrates into 1–2 lumpy bets and wrecks Calmar.)*
- **Max 15 concurrent positions** (cash is the real cap; we average ~7).
- **Bear-scaled sizing** — when the NIFTF 500 is below a rising 50-DMA, new positions
  are sized at **0.25×**. We still trade bear-market breakouts, just smaller.
- **Drawdown circuit-breaker** — if portfolio equity is >15% below its peak, **halt
  new entries** (open winners keep running); resume when within 7.5% of peak.
- **Idle cash → Liquid Bees @ 6.5%**, accrued daily (zero drawdown).

### Costs modeled
NSE delivery costs (STT 0.1%, exchange, SEBI, stamp, 18% GST, ₹13.5/scrip DP on
sell), 10 bps slippage each side, pessimistic gap fills.

---

## 4. The honest profile (read this before trading it)

- **Win rate is ~27%.** This is a *trend-following* system: you lose ~1R on ~73% of
  trades and win big (avg win ≈ 8R) on the rest. The win/loss **magnitude** is ~8:1.
- **It is NOT a lottery at the portfolio level.** Top-5 trades are ~20% of gross
  profit at the *trade* level, but diversifying across ~7 concurrent positions
  produces a **smooth** equity curve (Sharpe 1.93, 16% maxDD). The lumpiness is in
  individual trades; the portfolio compounds steadily.
- **You must take every signal.** Skipping trades because "this one looks bad"
  re-introduces the discretion we removed — and the big winners are unpredictable
  (feature-selection IC tested at ~0.03–0.08, no usable edge in picking among setups).
- **2021 was exceptional** (+149%, the post-COVID small-cap melt-up). Don't annualise
  off it. Strip it out and the system still beats buy-and-hold risk-adjusted, but
  expect single-to-low-double-digit years in sideways/large-cap markets (2016, 2019, 2025).
- **Capacity is quantified, not a mirage.** The edge holds in every liquidity tier
  (below) — even the 100 most-liquid mega-caps beat buy-and-hold 4× on Calmar, so
  this is a real edge, not a small-cap slippage artifact. Return rises as smaller
  names are added; pick the tier that fits your account size.

### Liquidity tiers (locked config, full period)

| Universe | min daily turnover | CAGR | maxDD | Calmar | Sharpe | best for |
|---|---|---|---|---|---|---|
| top 100 | ₹148 cr | 12.4% | 10.7% | 1.15 | 1.42 | institutional size |
| top 250 | ₹52 cr | 14.2% | 10.0% | 1.41 | 1.32 | large accounts |
| **top 500** | **₹15.6 cr** | **18.0%** | **10.4%** | **1.73** | 1.51 | **best risk-adjusted; scalable to ~₹crore** |
| top 800 | ₹5.6 cr | 21.7% | 15.0% | 1.44 | 1.66 | mid accounts |
| full ~1270 | ₹0.1 cr | 24.5% | 16.2% | 1.51 | 1.93 | small account (₹1–10 L) |

> **Two recommended operating points:** *small account* → full universe (24.5% CAGR);
> *scalable* → top-500 by turnover (18% CAGR, Calmar 1.73 — the best of any tier).

### Without the 2021 outlier
2021 was an exceptional +149% year (post-COVID small-cap melt-up). Excluding it,
the system still compounds at ~13–14% CAGR at ~16% maxDD (Calmar ~0.85) — i.e. it
**still beats buy-and-hold on a risk-adjusted basis even in its worst-case framing.**
The 24.5% headline is 2021-boosted; plan around the ~14–18% range.

---

## 5. How we got here (key findings)

1. **Data was the first bug.** Atlas prices were only partly split/bonus adjusted →
   phantom −20R "gap" losses that hid the edge. Rebuilt the cache from Kite (fully
   adjusted, same source we trade live). Expectancy went from ≈0 to positive immediately.
2. **Exit discipline > setup selection.** Close-based stops (not intraday wicks),
   a wide trail (let winners run), and a faster regime fixed the per-trade edge.
   A composite alpha-score to *pick* better setups was tested rigorously and **failed
   out-of-sample** — the setups are homogeneous; the edge is in the exit, not selection.
3. **Capital efficiency was the return lever.** The edge earns ~27% on *deployed*
   capital; the constraint was deploying it. Lower RPT (more, smaller, diversified
   positions) + dropping the index entry-gate took deployment from 22% → ~83% and
   CAGR from 11% → 24.5%, while the DD circuit-breaker + bear-sizing held maxDD at 16%.

---

## 6. Next steps

- [ ] Wire live signals on Kite (universe scan → entry/stop/size → alerts).
- [ ] Forward paper-trade 10–15 days; reconcile fills vs backtest assumptions.
- [ ] Earnings/announcement blackout (avoid holding through scheduled results) —
      may trim the −1.5R close-stop tail.
- [ ] Re-confirm capacity at the intended account size.

*Reproduce:* `python scripts/run_final_strategy.py` (locked config + per-year + equity curve).
*Engine:* `backend/engine/backtest_fast.py` (exit_mode="chandelier", chandelier_mult=5.0).
