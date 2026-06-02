# Strategy Handoff — start here in the next session

**Branch:** `claude/sweet-babbage-zGNuM`  ·  **PR:** #1  ·  **Full spec:** `STRATEGY_CARD.md`

Continuation point. We took the system from "loses money on bad data" to a
**walk-forward-validated swing strategy that beats NIFTY 500 buy-and-hold on every
risk-adjusted axis**, then stress-tested it across four research tracks. The
deployable answer is **v2** (Section 1). Section 5 is what's genuinely still open.

> ⚠️ **Rebuild data first.** `champion_cache.sqlite` (~231 MB, Kite-adjusted) is
> git-ignored. On a fresh clone: `python scripts/build_cache_kite.py` then
> `python scripts/build_index_cache.py` (needs Kite creds in `.env`). Without it,
> every backtest script errors on load.

---

## 1. Where we landed — two configs, v2 recommended

₹1,00,000 · 2016–2026 · **after NSE costs + liquidity-tiered slippage (10–100bps) + circuit-lock skip** (the honest cost model — the edge survives it):

| Config | win% | CAGR | maxDD | Calmar | OOS TEST Calmar | ex-2021 CAGR |
|---|---|---|---|---|---|---|
| v1 (no volume filter, RPT 0.25%) | 27% | ~24–27%* | 15.8% | 1.75 | 1.93 | 13.5% |
| **v2 (breakout ≥2× vol, RPT 0.35%)** | **35%** | **26.5%** | **14.8%** | **1.79** | **2.34** | **19.5%** |
| NIFTY 500 buy & hold | — | 13.4% | 44.8% | 0.30 | — | 12.0% |

\* v1's CAGR sits in a **~5% selection-noise band** (22.7–27.9%) — see Track 1. Quote a range, not a point.

**v2 is the recommended deployable config:** higher win rate (far easier to hold than 27%), lower drawdown, better out-of-sample Calmar, and **less 2021-dependent** (ex-2021 19.5% vs v1's 13.5%). Positive in **10 of 11 years** (only 2018, −5.9%).

## 2. The exact config (reproducible)

- **Universe (live floor DECIDED):** trade names ≥ **₹5cr/day turnover** (Phase-1 paper default; ≥ ₹15cr for large capital). The full ~1,270-name universe is **backtest-only** — its headline returns lean on unfillable sub-₹1cr micro-caps (see Track 5).
- **Entry (all must hold):** Stage S1B/S2 uptrend · volatility contraction true · avgTRP ≥ 2.0 · valid base (≥20 bars) · buy on break above 5-day high. **No index-regime gate.** **v2 adds: breakout-day volume ≥ 2× the 50-day average.**
- **Stop (loss-cut):** entry − 1×TRP, **close-based** (exit only on a *close* below the stop, or a gap-down at the open; intraday wicks don't exit).
- **Exit (profit):** `exit_mode="chandelier"`, **5×ATR trailing stop** (ratchets up only). **No fixed target** — ride until the trail breaks. Confirmed 100% mechanical, no look-ahead (`run_v2_trace.py` re-derives every exit forward).
- **Sizing:** RPT **0.35%** (v2) / 0.25% (v1) · max **15** concurrent · **bear-scaled 0.25×** when NIFTY 500 < rising 50-DMA · **15% portfolio DD circuit-breaker** (halt new entries, resume <7.5%) · idle cash @ 6.5%.
- **Same-day selection** (when signals > slots): highest risk-adjusted momentum rank — for *determinism* only (no edge; see Track 2).
- Engine: `backend/engine/backtest_fast.py::_fast_simulate` (toggles: `skip_circuit_locked`, `vol_breakout_k`, `vol_dryup`, `vol_filter_dates`). Slippage tiered in the harness.
- Reproduce v2: `python scripts/run_track3_volume.py` · per-year: `run_v2_yearly.py`.

## 3. Why it works (foundational findings)

1. **Data was the hidden bug** — Atlas prices were only partly split/bonus-adjusted → phantom −20R losses. Rebuilt from Kite (fully adjusted, = live source). Edge appeared.
2. **Exit discipline > setup-selection** — close-based stops + a wide trail made the edge. *Selection carries no edge* — confirmed THREE ways: a composite alpha-score failed OOS (IC 0.03–0.08), momentum-rank ≈ reverse-rank, and the entry filter already screens for quality. **The money is in the exit, not in picking setups.**
3. **Capital efficiency = the return lever** — lower RPT → ~7 diversified positions → deployment 22%→83% AND a smoother curve. CAGR 11%→24.5%.
4. **Not a micro-cap mirage** — works even in the 100 most-liquid mega-caps (Calmar 1.15); top-500 is the scalable sweet spot.

## 4. What we TESTED and CONCLUDED this session — DO NOT REDO

Four tracks, each A/B walk-forward validated. Scripts: `run_track{1,2,3,4}_*.py`, `run_v2_{yearly,diagnose,trace}.py`. Research basis: `RESEARCH_VOLUME_MOMENTUM.md`.

- **Track 1 — honest frictions: ADOPTED.** Tiered slippage + circuit-lock skip → edge *survives* (Calmar 1.70 vs optimistic 1.51). Exposed the ~5% selection-noise band.
- **Track 2 — momentum-rank selection: NO EDGE** (rank ≈ reverse-rank). Adopted for *determinism* only. Don't expect selection signals to help.
- **Track 3 — volume: the answer.** Volume **dry-up HURTS** (rejected). **Breakout ≥2× volume = v2** (win 27%→35%, meanR +1.39→+2.23, OOS Calmar 2.34). **Do NOT add OBV/CMF/A-D — debunked.**
- **Track 4 — regime-conditional filter (≥2× only when weak): DISCIPLINED NEGATIVE.** *Looks* best on full-period (29.2% CAGR) but it's a **2021 mirage** — it rides 2021 like v1 and gives up v2's 2023–25 edge (OOS Calmar 0.46, ex-2021 17.3% < v2's 19.5%). The 50-DMA regime is too crude to tell *easy*-bull (2017/20, filter hurts) from *selective*-bull (23/24, filter helps). **v2 stays.**
- **Why v2 shines post-2022 (`run_v2_diagnose.py`):** NOT because high-vol breakouts improved — because *low*-vol breakouts **collapsed** (+1.77R in 2016–21 → +0.27R post-2022) as the market got harder/more selective. The filter is a quality screen that only pays when quality matters. **Caveat: if a broad liquidity melt-up returns, expect v2 to lag v1 again** (as in 2020–21).
- **Honest trade reality (`run_v2_trace.py`):** ~65% of trades lose (median **−1.3R**; ~1-in-5 lose >1.5R because close-based stops let gaps through — losses are NOT capped at 1R). ~35% win (median **+5.2R**). **Top 5 trades = 47% of all profit** → outlier-driven, must take *every* signal. You never sell the top (5×ATR trail gives back ~20–25% from peak).

- **Track 5 — cap/liquidity expectancy + deployable tiers** (`run_v2_cap_diagnostic.py`, `run_v2_deployable_tiers.py`): the edge is **strongly cap-dependent**. Per-trade, mega/large (≥25cr) ≈ **0 edge** (meanR +0.07/+0.31); the money is in **mid (5–25cr, +2.63R, 35% of profit)** and **micro (<1cr, +7.15R, 50% of profit)**. At the portfolio level the headline 26.5% is **micro + 2021 inflated**: 2021 was **+114% FULL but +1.4% at ≥15cr** (the melt-up was entirely sub-15cr). **Deployable ex-2021 CAGR ≈ 18% (≥5cr) / 17.6% (≥15cr)** — still well above the index at ~⅓ the DD. The large-cap edge is **era-dependent** (dead 2016–22, strong 2023–26: ≥15cr +50/+46/+22/+18%). Elevates **survivorship bias** (#2) — the micro tail that inflates the headline is the most delisting-prone. **Live floor DECIDED: ≥5cr (paper) / ≥15cr (large capital). Plan around ~16–18%, not 26%.**

---

## 5. Open backlog (genuinely unresolved)

Ordered by value. **#1 is the real next step.**

1. **Forward paper-trade on live Kite (the only true OOS).** Wire scan → entry → stop → size → alerts; run 10–15 sessions; reconcile real fills vs the backtest's assumptions (esp. on thin names — the biggest winner ASAL +178R was an illiquid 2021 micro-cap that may not fill at size).
2. **Survivorship bias — quantify it.** Universe = symbols with data *today*; delisted failures are absent → inflates returns. Estimate the haircut (proxy delisting penalty). The biggest remaining honesty gap.
3. **NSE delivery-% conviction filter.** The one India-specific signal we couldn't test — `delivery_pct` column is empty; needs a bhavcopy ingester. A natural complement to the volume filter.
4. **Breadth/dispersion regime — EXPLORATION ONLY.** Track 4 showed the *right* regime lever is breadth (broad melt-up vs narrow leadership), not index trend. But building it now — *because we know 2023–24 needed it* — is textbook overfitting on ~10 years / 2–3 cycles. Only pursue with heavy skepticism and out-of-sample discipline; do not deploy on a backtest alone.
5. **Entry-parameter robustness.** Base/contraction/trigger params are legacy defaults, never swept. Sweep them; show a **plateau, not a peak** (anti-overfit evidence). Exit/sizing params already shown to be a stable plateau.

## 6. File map

- `STRATEGY_CARD.md` — full spec, metrics, caveats, liquidity tiers, §6 = the v2/research refinements.
- `RESEARCH_VOLUME_MOMENTUM.md` — cited volume/momentum literature review (what to try, what's debunked).
- `scripts/run_track1_honesty.py` — frictions + selection-noise. `run_track2_momentum.py` — momentum-rank A/B.
- `scripts/run_track3_volume.py` — **v2** (volume filters + redeploy). `run_track4_regime.py` — regime-conditional (negative).
- `scripts/run_v2_yearly.py` — per-year v1/v2. `run_v2_diagnose.py` — why post-2022. `run_v2_trace.py` — mechanical-exit proof + R-distribution.
- `scripts/run_final_strategy.py` — v1 locked config. `run_strategy_wf.py` — walk-forward. `run_liquidity_robustness.py` — capacity tiers.
- Engine: `backend/engine/backtest_fast.py` (close-based stop + chandelier exit + circuit/volume/regime toggles). 20+ engine tests pass.
