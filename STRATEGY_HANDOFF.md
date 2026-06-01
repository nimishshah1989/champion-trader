# Strategy Handoff — start here in the next session

**Branch:** `claude/sweet-babbage-zGNuM`  ·  **PR:** #1  ·  **Full spec:** `STRATEGY_CARD.md`

This is the continuation point. We took the system from "loses money on bad data"
to a **walk-forward-validated swing strategy that beats NIFTY 500 buy-and-hold on
every axis.** You're not fully convinced and want to push further — Section 4 is
the backlog to do exactly that.

---

## 1. Where we landed (the result)

Champion Trend System, ₹1,00,000, 2016–2026, **after NSE costs + 10bps slippage:**

| | CAGR | maxDD | Calmar | Sharpe |
|---|---|---|---|---|
| **The system** | **24.5%** | **16.2%** | **1.51** | **1.93** |
| NIFTY 500 buy & hold | 13.4% | 44.8% | 0.30 | 0.55 |

- **Out-of-sample** (params chosen on 2016-20, applied blind to 2021-26): 20.9% CAGR, 11% DD, Calmar 1.89.
- ₹1L → ₹9.2L (vs buy-and-hold ₹3.6L). Positive 8 of 11 years; worst year −9.4%.
- Edge holds in every liquidity tier — top-500 (₹15cr+ turnover) is the scalable sweet spot: 18% CAGR, 10% DD, **Calmar 1.73**.

## 2. The exact locked config (reproducible)

- **Universe:** ~1,270 NSE names with data (or top-500 by turnover for scale).
- **Entry (all must hold):** Stage S1B/S2 uptrend · volatility contraction true · avgTRP ≥ 2.0 · valid base (≥20 bars) · buy on break above 5-day high. **No index-regime gate.**
- **Stop:** entry − 1×TRP, **close-based** (exit only on a close below stop, or gap-down at open; intraday wicks don't exit).
- **Exit:** `exit_mode="chandelier"`, **5×ATR trailing stop** (ratchets up only). No fixed target — let winners run.
- **Sizing:** RPT **0.25%** · max **15** concurrent · **bear-scaled 0.25×** when NIFTY 500 < rising 50-DMA · **15% portfolio DD circuit-breaker** (halt new entries, resume <7.5%) · idle cash @ 6.5%.
- Engine: `backend/engine/backtest_fast.py::_fast_simulate`. Reproduce: `python scripts/run_final_strategy.py`.

## 3. Why it works (the 4 findings)

1. **Data was the hidden bug** — Atlas prices were only partly split/bonus-adjusted → phantom −20R losses. Rebuilt from Kite (fully adjusted). Edge appeared.
2. **Exit discipline > setup-selection** — close-based stops + wide trail made the edge; a composite "pick better setups" score **failed OOS** (feature IC 0.03–0.08).
3. **Capital efficiency = the return lever** — lower RPT → ~7 diversified positions → deployment 22%→83% AND smoother curve. CAGR 11%→24.5%.
4. **Not a micro-cap mirage** — works even in the 100 most-liquid mega-caps (Calmar 1.15).

---

## 4. Where to push next (the "not convinced / improve more" backlog)

Ordered by expected value. **#1 is the most promising and uses your own intuition.**

1. **VOLUME + MOMENTUM-RANK — researched; see `RESEARCH_VOLUME_MOMENTUM.md`.** The entry
   uses only price/ATR. The research (5-agent lit/repo/Indian-market review) says volume
   is **not** a magic win-rate booster (naive volume-on-breakout filters test as noise;
   OBV/CMF/A-D are debunked — **do not add them**), but three things have real,
   corroborated support and are pre-registered for an A/B walk-forward test:
   (a) **base volume dry-up** (Minervini + Lee-Swaminathan low-turnover persistence),
   (b) a **strong** breakout-volume gate (≥2×, not weak +10%), used to confirm/select,
   (c) **risk-adjusted momentum rank** (the NSE index formula `0.5·z(6m/σ)+0.5·z(12m/σ)`)
   to pick which breakouts to take when signals > capacity — best-grounded, attacks
   2021-dependence. Validate with Deflated Sharpe (count trials) on full + top-500 tiers.
   Expect a *modest* lift, not a step-change. Plus a fast-follow: NSE **delivery-%**
   conviction filter (needs bhavcopy ingest — `delivery_pct` column is empty).

2. **Kill the 2021 dependence.** The 24.5% headline leans on 2021's +149% (small-cap
   melt-up); ex-2021 it's ~13–14% CAGR. Re-validate with (a) multiple train/test split
   years, (b) a rolling 3-yr-in/1-yr-out walk-forward, (c) report median annual return
   not just CAGR. If it survives without 2021, that's the conviction you're missing.

3. **Win rate without wrecking returns.** Exits to raise win-rate already tested and
   FAILED (ladder/hybrid → Calmar 0.27–0.57). So the lever must be **entry quality**:
   volume (#1), RS vs index, distance-from-MA (avoid extended entries), sector breadth.
   Goal: 27% → 35%+ win while keeping the 5×ATR runners.

4. **Entry-parameter robustness.** The base/contraction/trigger params are legacy
   defaults, never swept. Sweep them and show a **plateau, not a peak** — strongest
   anti-overfit evidence. (Exit/sizing params already shown to be a stable plateau.)

5. **Survivorship bias — quantify it.** Universe = symbols with data *today*; delisted
   failures are absent, which inflates returns. Estimate the haircut (e.g., add a proxy
   delisting penalty) so the number is honest.

6. **Forward paper-trade on live Kite (the only true OOS).** Wire scan→entry→stop→size
   →alerts, run 10–15 sessions, reconcile real fills vs the backtest's assumptions.

## 5. File map & reproduce

- `STRATEGY_CARD.md` — full spec + validated metrics + honest caveats + liquidity tiers.
- `scripts/run_final_strategy.py` — locked config, per-year, equity curve.
- `scripts/run_strategy_wf.py` — walk-forward train/test. `run_exit_shootout.py` — exit comparison.
- `scripts/run_strategy_search.py` — risk-overlay grid. `run_liquidity_robustness.py` — capacity tiers. `run_deploy_test.py` — index-gate on/off.
- Engine change this arc: `backend/engine/backtest_fast.py` (close-based stop + `chandelier`/`hybrid`/`target_close` exits). 77 engine tests pass.

> ⚠️ **Rebuild data first.** `champion_cache.sqlite` (~231 MB, Kite-adjusted) is
> git-ignored, so a fresh clone won't have it. Before running any script:
> `python scripts/build_cache_kite.py` then `python scripts/build_index_cache.py`
> (needs Kite API credentials in `.env`). Without it, every script will error on load.
