# Volume & Momentum Research — Synthesis for the Champion Trend System

*Five parallel research agents (practitioner rules · academic literature · GitHub
implementations · Indian-market context · indicator evidence & overfitting),
cross-checked for corroboration. Goal: decide what volume/momentum signals to add
to our contraction-breakout entry to raise the 27% win rate, filter false
breakouts, and cut 2021-dependence — without repeating the overfit that killed the
composite alpha-score.*

---

## 0. The honest bottom line (read this first)

**Volume is not a magic win-rate booster, and the evidence says so.** The cleanest
head-to-head test found that adding a *weak* volume filter (+10% over average) to a
breakout lifted returns by ~1.25% — which the authors flagged "might be completely
due to randomness." The famous "RVOL > 2× → 82% win rate" numbers are **uncited
marketing**. OBV / Chaikin Money Flow / A-D line are **debunked** as standalone
edges (Chaikin zero-cross backtested at ~2.4% CAGR) and are mechanically redundant
with price.

**But three uses of volume have real, convergent support**, and one *momentum*
construct is better-grounded than any volume indicator:

1. **Volume dry-up in the base** — supported by both practitioners (Minervini) AND
   academia (Lee-Swaminathan: low-turnover winners have the most *persistent*
   momentum). The single best-corroborated idea here.
2. **A *strong* breakout-volume threshold (≥2×), used to confirm/select** — every
   practitioner and the only GitHub repo with published stats (Qullamaggie, 56% 10-day
   win) use it; the skeptics only debunk the *weak* version. Test it, expect modest.
3. **Risk-adjusted price momentum rank** (the NSE index formula) — to choose *which*
   breakouts to take when we have more signals than capital. Best-grounded of all.

Everything must be validated by A/B vs the price-only baseline, walk-forward, net of
costs, with the number of thresholds tried counted (Deflated Sharpe). Expect a
*modest* lift, not a step-change.

---

## 1. What the evidence says (corroborated findings)

### 1a. Volume dry-up in the base — STRONGEST support (3 independent agents agree)
- **Practitioner:** Minervini VCP requires volume to contract to <50% of the 50-day
  average through the base, with 3-5 ultra-low-volume days before the pivot.
  Wyckoff's "no-supply"/"spring" is the same idea (low-volume test = supply exhausted).
- **Academic:** Lee & Swaminathan (2000), *Price Momentum and Trading Volume* (JF 55) —
  **low-volume winners show the most persistent momentum** (continuation up to 3 yrs),
  high-volume winners reverse faster. Replicated in 34/37 countries (Bornholt-Malin).
  → A low-turnover base is the academically-favoured state.
  https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00280
- **Code precedent:** Screeni-py `validateLowestVolume(30)` (recent vol == 30-day min);
  xang1234 `volume < 0.8 × SMA50(volume)` counted over 10 days.
- **Caveat (agent 5):** no *transparent* standalone backtest isolates VDU's edge; the
  90%+ "VCP success rate" floating around is regime-conditioned & in-sample. Treat the
  *direction* as supported, the *magnitude* as unproven.

### 1b. Breakout-day volume — thresholds CONVERGE, but evidence says use a STRONG one
- Practitioner thresholds line up tightly: O'Neil **≥1.4-1.5×** (his stated "40-50%
  above normal"), Minervini ≥1.4× (prefers ≥2×), **Weinstein ≥2×** (weekly).
- GitHub thresholds: RyanJHamby 1.5×, Screeni-py/PKScreener **2.5×**, Qullamaggie **3×**.
- **The catch (agent 5 + agent 2):** the *weak* filter is noise; Lee-Swaminathan warns
  high-volume winners can *reverse faster*. The credible edge is at **extreme** relative
  volume used for **selection** (Zarattini-Aziz "Stocks in Play", ~2.4 Sharpe — though
  that's *intraday*). Gervais-Kaniel-Mingelgrin (2001) "High-Volume Return Premium":
  volume spikes predict ~+0.5%/month — real but modest.
- **Verdict:** test breakout-volume confirmation at a **strong** threshold (≥2×), as an
  A/B toggle. Expect it to cut trade count and *maybe* lift win rate. Don't use weak (+10%).

### 1c. Risk-adjusted price momentum — the best-grounded signal (not volume at all)
- The official **Nifty200 Momentum 30 / Midcap150 Momentum 50** score (agent 4):
  `0.5·z(6m return ÷ 1yr σ) + 0.5·z(12m return ÷ 1yr σ)`. **No volume term** — it's
  pure volatility-scaled momentum. Battle-tested institutional benchmark, fully
  reproducible from our data.
- Backed by Jegadeesh-Titman (cross-sectional momentum ~1%/mo) and George-Hwang
  (52-week-high momentum that **doesn't reverse** long-run — ideal for hold-the-winner).
  https://www.bauer.uh.edu/rsusmel/phd/jegadeesh-titman93.pdf
- **Use:** rank candidate breakouts by this score and take the strongest first when
  signals > capacity. Directly attacks capital allocation AND 2021-dependence.

### 1d. Pocket Pivot & Up/Down-volume — crisp, secondary
- **Pocket Pivot** (Morales-Kacher): an up-day whose volume exceeds the **highest
  down-day volume of the prior 10 days**, near the 10/50-DMA. The cleanest codifiable
  rule found — no fuzzy threshold. Test as an alternate entry trigger.
- **Up/Down volume ratio (50d) ≥ 1.0** (O'Neil accumulation; coded in atanuc073,
  xang1234). A quality gate, modest expected effect.

---

## 2. Conflicts to respect (don't assume a side)

1. **Liquid vs illiquid momentum premium (India).** Academic (Chui-Ranganathan 2023):
   NSE momentum is strongest in *liquid* names. Practitioner (freefincal, 18.5yr): the
   premium lives in the *illiquid* half (19.4% vs 8.5% net CAGR). **Our** liquidity-tier
   test slopes toward small-caps — consistent with the illiquidity-premium view, which
   means **part of our 24.5% may not be capturable at scale.** Keep reporting by tier;
   **treat top-500 (Calmar 1.73, ₹15cr+ turnover) as the defensible result.**
2. **High volume ≠ unconditionally bullish.** Llorente et al. (2002): high-volume moves
   *continue* in high-info-asymmetry stocks (small/mid — our universe ✓) but *reverse*
   in liquid large-caps. So breakout-volume confirmation is more valid where we trade.

---

## 3. What to AVOID (saves us from the overfitting trap)

- **OBV, Accumulation/Distribution line, Chaikin Money Flow, VWAP** — no credible
  out-of-sample edge; redundant with price; VWAP is an execution benchmark. The
  data-snooping literature (Sullivan-Timmermann-White 1999; Bajgrowicz-Scaillet 2012;
  ~50% of published trading-rule wins are false discoveries) says a single indicator
  picked because it backtested well will not survive correction. *This is exactly how
  our composite alpha-score failed OOS — don't repeat it.*

---

## 4. Make-it-honest improvements (separate track, from Indian-market agent)

Independent of volume, our backtest likely *overstates* small-cap returns:
- **Impact-cost slippage, not flat 10bps.** NSE's official liquidity metric; small/mid
  caps run far above 10bps. Model slippage as a function of position size ÷ ADV.
- **Circuit-lock fill check.** A real breakout can hit the upper price band (2/5/10/20%)
  and be *unfillable*; we currently assume it fills. Skip/penalise entries whose
  breakout-day move ≥ the band.
- These tighten the honest number and matter most in exactly the illiquid tail that
  inflates the headline CAGR.

---

## 5. Validation protocol (pre-registered — anti-overfitting)

Test this SMALL, fixed set (keep N low so the Deflated-Sharpe haircut is small):

| # | Signal | Exact rule | Data | Use |
|---|---|---|---|---|
| A1 | Base volume dry-up | breakout-bar setup requires `min(vol, last 30d)` in base OR `mean(vol,10) < 0.8·SMA50(vol)` | now | filter |
| A2 | Strong breakout volume | breakout-bar `vol ≥ K · SMA50(vol)`, K ∈ {1.5, 2.0, 2.5} | now | filter |
| A3 | Momentum rank | take top-N candidates by `0.5·z(6m/σ)+0.5·z(12m/σ)` when signals>capacity | now | allocate |
| B1 | Pocket pivot trigger | up-day `vol > max(down-day vol, last 10d)` near 10/50-DMA | now | trigger |
| B2 | Up/Down vol gate | `Σup-vol(50) / Σdn-vol(50) ≥ 1.0` | now | gate |
| C1 | Delivery % conviction | `delivery% > N-day avg` & top universe pct | **needs bhavcopy ingest** | filter |

**Rules of engagement:**
1. **A/B against the locked price-only chand5x baseline**, identical entries/exits/sizing, net of costs. The filter must beat baseline on **walk-forward TEST (2021-26 blind)**, not just full-period.
2. **Count trials.** ~6 signals × a few thresholds ≈ N≈10. Apply Deflated Sharpe
   (E[max Sharpe of N noise strategies] ≈ √(2·ln N) ≈ 2.1 — so demand a real margin).
   https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
3. **Fewer trades = wider error bars.** A filter that cuts trades 50% needs a clearly
   bigger win-rate lift to be real. Report trade count + bootstrap CI on expectancy.
4. **Keep what survives TEST, discard the rest.** Default expectation: 1-2 of these
   survive with a *modest* lift. That's success — not a step-change.

---

## 6. Recommended next-session plan

1. Implement A1 (dry-up) + A2 (strong breakout vol) as optional entry gates in
   `_fast_simulate`; A3 (momentum rank) as a candidate-ranking step in the portfolio walk.
2. Run the A/B walk-forward harness (reuse `run_strategy_wf.py`) for each, net of costs,
   on both full-universe and **top-500** tiers.
3. If A1/A2/A3 help on TEST → keep; then add the honesty track (impact-cost slippage +
   circuit check) and re-confirm.
4. If delivery-% looks worth it, write an NSE bhavcopy ingester to fill the empty
   `delivery_pct` column, then test C1.

**Key sources:** Lee-Swaminathan 2000 (JF) · Jegadeesh-Titman 1993 (JF) · George-Hwang
2004 (JF) · Llorente-Michaely-Saar-Wang 2002 (RFS) · Gervais-Kaniel-Mingelgrin 2001 (JF) ·
Sullivan-Timmermann-White 1999 (JF) · Bailey-López de Prado (Deflated Sharpe) ·
NiftyIndices Momentum methodology · freefincal liquidity-illusion · QuantifiedStrategies
breakout/Chaikin backtests · GitHub: xang1234/stock-screener, pkjmesra/PKScreener,
pranjal-joshi/Screeni-py, VladPetrariu/Qullamaggie-breakout-scanner, atanuc073/stock-analysis.
