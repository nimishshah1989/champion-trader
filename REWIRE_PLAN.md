# Rewire Plan — making the live app trade the validated v2 strategy

**Status:** blueprint only (no code). Read `STRATEGY_HANDOFF.md` (validated v2) and
`STRATEGY_CARD.md` (full spec) first. This document maps the validated `backend/engine`
logic onto the live app (`backend/services`, `backend/routers`, `backend/intelligence`,
the scheduler, the 21 tables) and says exactly what to keep, replace, build, and delete.

> **One-line problem statement:** the strategy we validated and the app that runs live
> are two different programs that share a database. **No live service imports
> `backend.engine`** (grep: 26 hits, every one *inside* `backend/engine/` itself).
> The live app runs an older, never-validated strategy.

---

## 0. The core finding (why this is bigger than "import the engine")

There are **two parallel implementations** of the whole strategy:

| | Validated (what we proved) | Live (what actually runs) |
|---|---|---|
| Setup detection | stage + contraction + base + avgTRP≥2 + 5-day-high break + **≥2× vol** | PPC/NPC/Contraction candle patterns (`trp_ratio≥1.5`, `vol_ratio≥1.5` /20d) |
| Stop | `entry − 1×TRP`, **close-based** | `entry − 1×TRP`, **intraday touch** |
| Profit-taking | **none** — ride a **5×ATR chandelier trail** | **2R/4R/8R/12R ladder** (book 20/20/40/80%) |
| Sizing | RPT **0.35%** | RPT **0.5%** |
| Risk caps | max **15** pos · bear **0.25×** · **15% DD** breaker | autopilot caps at 5 · **none** · **none** |
| Data | Kite-adjusted daily bars (`champion_cache.sqlite`) | **yfinance**, 9-month window, fetched live |
| Backtester | `engine/backtest_fast.py` (validated) | `services/backtest_engine.py` (separate, unvalidated) |

And the validated side is **not one callable unit** — it is spread across three layers,
only a sliver of which is packaged for reuse:

1. **Per-symbol entry+exit** — `engine/backtest_fast.py::_fast_simulate`
   (`exit_mode="chandelier"`, `chandelier_mult=5.0`, `vol_breakout_k=2.0`,
   `skip_circuit_locked=True`, `min_trp=2.0`). Exit logic is **inlined in the backtest
   loop** — not exposed as a per-bar function (only `_chandelier_stop` is extractable).
2. **Portfolio / risk overlay** — the `portfolio()` function **inside the research
   scripts** (`scripts/run_track3_volume.py`, `run_track4_regime.py`): RPT 0.35%, max 15,
   bear 0.25× via `load_regime(..., sma_window=50, slope_lb=5)`, 15% DD halt / 7.5%
   resume, idle cash @6.5%, momentum-rank same-day ordering, `CostModel`. **This is not
   in `backend/engine` at all** — it lives in `scripts/`.
3. **Slippage tiering** — `slip(adt)` (10/25/50/100 bps) in the harness.

**`engine/production_signal.py` is a half-built bridge that covers only a subset of
Layer 1:** it returns `(trigger, stop_distance)` for **v1 entry rules** — **no exits, no
≥2× volume gate, no regime, no sizing.** It is imported by nothing.

> **Therefore the first real task is *extraction*, not *integration*.** We must lift the
> validated logic out of the backtest loop and the scripts into a production runtime
> module, prove it reproduces the backtest trade-for-trade, and only *then* wire the live
> services to it. Wiring the services to `production_signal.py` as-is would ship **v1
> without exits** — worse than today.

---

## 1. Gap audit — per live service vs validated v2

Legend: ✅ matches v2 · ⚠️ partial/different · ❌ absent · 🔵 not v2's job (keep)

### 1a. Scanner — `services/scanner_engine.py` (+ `baseline_scanner.py`)
Drives the `daily_scanner` 16:00 job and `POST /scanner/run`.

| v2 entry rule | Live scanner | Status |
|---|---|---|
| Stage S1B/S2 **gate** | computed, used only as watchlist *label* — an S4 stock still passes | ❌ |
| Volatility contraction **gate** | exists only as one of 3 *separate* scans; PPC/NPC have none | ⚠️ |
| avgTRP ≥ 2.0 | never compared to 2.0; only `trp_ratio ≥ 1.5` (relative) | ❌ |
| Valid base ≥ 20 bars **gate** | `has_min_20_bar_base` computed, never enforced; label only | ❌ |
| Buy on break of **5-day high** | trigger = last-bar High (PPC) / 5-bar max High (contraction) — not a forward break rule | ❌ |
| Breakout-day vol ≥ **2× 50-day** | no 50-day vol computed anywhere; closest is `vol_ratio≥1.5` /20d on the signal candle | ❌ |
| Data = Kite-adjusted | **yfinance**, 9-month (~185 trading days), no cache | ❌ |

Net: the live scanner implements **none** of the six v2 gates as enforced filters. It is
a different setup detector on a different, shorter, differently-adjusted data feed.
Thresholds live in `intelligence/strategy.py::PARAMETERS` (3 of which — `sma_window`,
`stage_sma_lookback`, `contraction_atr_lookback` — are **dead**: the code hard-codes them).

### 1b. Position calculator — `services/position_calculator.py`
| Aspect | Live | v2 | Status |
|---|---|---|---|
| Stop formula | `entry − 1×TRP` | `entry − 1×TRP` | ✅ |
| Share count | `risk_amount / stop_distance` | same | ✅ |
| RPT default | **0.5%** (caller-supplied) | **0.35%** | ⚠️ |
| Targets | computes 2R/NE/GE/EE | v2 has no targets | ⚠️ (unused under v2) |
| Risk caps | none here | (applied elsewhere) | 🔵 |

The sizing *primitive* is correct; only the RPT default and the (now-unneeded) target
outputs differ. **This is the smallest gap of any service.**

### 1c. Paper trading — `services/paper_trading.py`
| Aspect | Live | v2 | Status |
|---|---|---|---|
| Stop trigger | **intraday touch** (`current_price <= sl_price`) | **close-based** | ❌ |
| Stop movement | **static**, never trails | **5×ATR chandelier**, ratchets up | ❌ |
| Profit-taking | **2R/4R/8R/12R ladder** | none — ride the trail | ❌ |
| Max open risk | 10% cap (enforced) | ~5.25% implied | ⚠️ |
| Max concurrent | **none** | **15** | ❌ |
| Bear sizing | **none** | 0.25× | ❌ |
| DD breaker | **none** | **15%** | ❌ |
| Data | yfinance snapshot | daily close | ❌ |

This is a **different exit engine entirely** — the Champion ladder, not the v2 trail.

### 1d. Price monitor / action alerts — `services/price_monitor.py` + `price_monitor_alerts.py`
Drives `entry_monitor` (1 min, 15:00–15:30) and `exit_monitor` (2 min).
- **Entry** (`check_buy_signals`): fires when `current_price ≥ trigger_level` in the last
  30 min. ✅ *the last-30-min timing matches the methodology* — but no ≥2× volume
  confirmation, and the trigger came from the legacy scanner.
- **Exit** (`check_sell_signals`): **intraday touch** SL (❌ close-based), then the
  **2R/4R/8R/12R ladder** (❌), **no trailing stop** (❌).
- **Feed**: yfinance `last_price` snapshot polled on a timer → the SL is **structurally
  intraday**. It *will* fire on an intra-session dip that closes back above the stop —
  the exact behavior v2 was designed to avoid (measured: hard intraday stops = 78%
  premature exits, −10pts win rate). ❌ **This is a feed problem, not only a logic bug.**

### 1e. Autopilot — `services/autopilot.py`
Hard-coded: `VIRTUAL_CAPITAL=100000`, `RPT_PCT=0.50` (❌ 0.35), `MAX_POSITIONS=5`
(⚠️ v2=15), `MAX_OPEN_RISK_PCT=10`, `MIN_TRP=2.0` (✅). Pipeline
`scan→watchlist→BUY→trade→SELL→exit` is structurally right (✅ the orchestration we want)
but every step calls **services** logic (legacy scanner, `position_calculator`, ladder
exits via the alert path). No bear-sizing, no DD breaker, no chandelier (❌). Writes a
`ShadowTrade` per buy (good — keep). Imports `position_calculator` + `regime_classifier`,
never `backend.engine`.

### 1f. Alerts / notifications — `services/alert_service.py`, `notifications.py`
- `app_alerts` = passive UI feed (`alert_service.create_alert`). 🔵 keep.
- `action_alerts` = the BUY/SELL workflow (created in `price_monitor`). 🔵 keep the
  table & workflow; the *content* must come from the v2 runtime.
- **Telegram is barely wired**: only `risk_guardian` breaches + the CIO daily brief call
  Telegram. The autopilot BUY/SELL action alerts are **UI-only** — `send_entry_alert` /
  `send_sl_alert` exist but have **no callers**. ⚠️ wire these for a live system.

### 1g. Backtester — `services/backtest_engine.py`
Used by `/simulation/backtest` **and** the overnight `autooptimize`. It is the
**unvalidated** backtester (imports `strategy.PARAMETERS`, `position_calculator`,
`trading_rules`). ❌ It is not `engine/backtest_fast.py`. **Two backtesters coexist; only
one is validated.**

---

## 2. Single source of truth — the target architecture

**Principle:** one validated strategy core; the live app and the backtester both call it.

### 2.1 Build a runtime package: `backend/engine/runtime/` (new)
Extract the validated logic (today entangled in `_fast_simulate` + `scripts/`) into three
pure, reusable, unit-tested modules:

1. **`signal_service.py`** — the v2 *entry* signal.
   - `evaluate_entry(history: list[Bar]) -> EntrySignal | None`
   - Reuses `precompute_features` / `classify_watch_state` (stage+contraction+base),
     `min_trp≥2.0`, the 5-day-high `trigger_level`, **plus the ≥2× breakout-volume gate**
     (`vol_sma50`) and the **circuit-lock skip** — i.e. it *upgrades*
     `production_signal.py` from v1 to **v2**. Returns `(trigger, stop_distance,
     avg_trp, volume_ratio, signal_type)`.
   - **Replaces** `production_signal.py` (or production_signal becomes a thin v1 alias).
2. **`exit_service.py`** — the v2 *exit* (the part that doesn't exist outside the loop).
   - `init_stop(entry, stop_distance) -> TrailState` and
     `step(trail: TrailState, bar: Bar, atr: Decimal) -> ExitDecision` implementing the
     **close-based stop + 5×ATR chandelier ratchet** (lift from `_fast_simulate`
     lines 84–98; reuse `_chandelier_stop`). One call per symbol per day.
   - This is the single most valuable extraction — it's the source of the edge and it is
     currently un-callable.
3. **`risk_manager.py`** — the portfolio overlay (today only in `scripts/portfolio()`).
   - RPT 0.35% sizing, **max 15** positions, **bear 0.25×** (reads `load_regime(...,
     sma_window=50, slope_lb=5)` — **note: 50-DMA, not the 150-DMA default**), **15% DD
     halt / 7.5% resume**, same-day momentum-rank ordering, tiered slippage, `CostModel`.

### 2.2 Parity harness (the acceptance gate)
`scripts/run_runtime_parity.py`: feed the cache through the **runtime** day-by-day and
assert it reproduces `engine/backtest_fast.py` v2 **trade-for-trade** (same entries,
exits, R-multiples) on 2016–2026. **No live wiring proceeds until parity is green.**
This is what makes the runtime *trustably* the validated strategy.

### 2.3 Re-point the live services (thin adapters, not rewrites)
- `scanner_engine.run_all_scans` → call `signal_service.evaluate_entry` across the
  universe; write the **same `scan_results` columns** (they already exist:
  `avg_trp`, `volume_ratio`, `stage`, `trigger_level`, `watchlist_bucket`).
- `position_calculator.calculate_position` → keep the primitive; default RPT 0.35; stop
  feeding 2R/NE/GE/EE into trades (v2 doesn't use them).
- `paper_trading` + `price_monitor_alerts` exit paths → replace ladder/intraday-touch
  with `exit_service.step` on the **daily close**.
- `autopilot` constants → RPT 0.35, MAX_POSITIONS 15, and route sizing through
  `risk_manager` (adds bear-sizing + DD breaker).
- `/simulation/backtest` + `autooptimize` → call `engine/backtest_fast` (the validated
  one), retiring `services/backtest_engine.py`.

### 2.4 Keep / replace / delete

| Verdict | Items |
|---|---|
| **Keep (reuse)** | all 21 tables & routers; `position_calculator` primitive; autopilot *orchestration*; `action_alerts`/`app_alerts` workflow; `shadow_trades` (already engine-shaped); `regime_log`; `notifications` (Telegram) — just add callers; the last-30-min entry-window design |
| **Replace (point at runtime)** | `scanner_engine` setup detection; `paper_trading` + `price_monitor_alerts` exit logic; autopilot risk constants; `production_signal.py` (→ v2 `signal_service`) |
| **Delete / retire** | `services/backtest_engine.py` (after `/simulation` + `autooptimize` move to `engine/backtest_fast`); the dead PARAMETERS (`sma_window`, `stage_sma_lookback`, `contraction_atr_lookback`); the 2R/4R/8R/12R ladder constants in `trading_rules.py` (once v2 trail is the default) |
| **Decommission carefully** | the PPC/NPC candle scanners — *or* keep them as **labels only** (they don't gate v2 entries); the `baseline_scanner` A/B should compare **v2 vs legacy**, not optimized-vs-default legacy |

---

## 3. End-to-end live data flow (target)

```
┌─ DATA INGEST (new/repointed) ──────────────────────────────────────────────┐
│ Kite adjusted daily bars  → `bars` table   (per symbol, ≥252 bars retained) │
│ NIFTY 500 daily closes     → `index_bars` table  (engine `load_regime` reads)│
└──────────────────────────────────────────────────────────────────────────-─┘
        │  (16:00 IST, after close)
        ▼
┌─ DAILY SCAN ───────────────────────────────────────────────────────────────┐
│ for each symbol: precompute_features → signal_service.evaluate_entry         │
│   → if v2 setup: write scan_results (trigger, avg_trp, vol_ratio, stage…)    │
│ regime_classifier writes today's bull/bear flag (NIFTY500 vs rising 50-DMA)  │
└──────────────────────────────────────────────────────────────────────────-─┘
        │
        ▼
┌─ WATCHLIST (READY/NEAR/AWAY) ──────────────────────────────────────────────┐
│ autopilot.post_scan_populate: admit READY/NEAR, liquidity-filtered, trp≥2   │
│   → watchlist rows carry trigger_level + planned sizing                      │
└──────────────────────────────────────────────────────────────────────────-─┘
        │  (15:00–15:30 IST next session — last 30 min)
        ▼
┌─ ENTRY TRIGGER ────────────────────────────────────────────────────────────┐
│ entry_monitor: price breaks trigger_level → CONFIRM ≥2× vol (EOD-projected)  │
│   → risk_manager.size(equity, 0.35%, stop_dist, bear_mult, caps) → BUY alert │
│   → not circuit-locked → create Trade (close-based stop, trail initialised)  │
└──────────────────────────────────────────────────────────────────────────-─┘
        │
        ▼
┌─ ORDER (Phase 1 paper → Phase 2 Kite/Zerodha live) ────────────────────────┐
│ Phase 1: paper fill at break price + tiered slippage                        │
│ Phase 2: live order via Kite Connect order API (same provider as the feed)  │
└──────────────────────────────────────────────────────────────────────────-─┘
        │  (once daily, at/after close)
        ▼
┌─ EXIT MONITORING (close-based) ────────────────────────────────────────────┐
│ exit_service.step(trail, daily_bar, atr):                                    │
│   close < stop OR gap-down open ≤ stop → SELL all (exit)                     │
│   else ratchet stop = max(stop, highest_high − 5×ATR)  → persist new stop    │
│ risk_guardian: enforce 15-pos cap, 15% DD halt, max open risk               │
└──────────────────────────────────────────────────────────────────────────-─┘
        │
        ▼
┌─ JOURNAL / ALERTS ─────────────────────────────────────────────────────────┐
│ trades / partial_exits updated; r_multiple computed; ShadowTrade reconciled  │
│ Telegram: entry fills, SL/exit fills, daily CIO brief (wire send_* callers)  │
└──────────────────────────────────────────────────────────────────────────-─┘
```

---

## 4. Scheduled jobs — what changes

| Job (IST) | Change | Detail |
|---|---|---|
| `corpus_updater` 17:30 | **Repurpose → DATA INGEST** | Populate `bars` (Kite-adjusted, ≥252 retained) + `index_bars`. Foundational — the engine reads these. Today data is yfinance, ad-hoc, 9-month. |
| `daily_scanner` 16:00 | **Replace scan core** | Call `signal_service.evaluate_entry` (v2) instead of `scanner_engine` PPC/NPC. Keep the autopilot + baseline hooks; baseline becomes **v2 vs legacy** A/B. |
| `regime_classifier` 16:45 | **Add v2 bear flag** | Keep ADX/VIX classification; *add* the simple NIFTY500-vs-rising-**50-DMA** boolean the `risk_manager` reads for bear-sizing. |
| `entry_monitor` 15:00–15:30 | **Keep timing, fix logic** | Last-30-min trigger-break is correct. Add ≥2× volume confirmation + route sizing through `risk_manager`; reject circuit-locked breakouts. |
| `exit_monitor` every 2 min | **Fundamental change** | v2 is **close-based daily**, not 2-min intraday-touch. Replace with **one post-close evaluation** (`exit_service.step` on the daily bar); handle gaps at next-open. The 2-min snapshot loop is removed (or demoted to a non-binding watch). **This is the riskiest job to get wrong.** |
| `risk_guardian` every 10 min | **Promote to enforcer** | Today: Telegram warnings only. Make it enforce the **15-position cap, 15% DD halt/7.5% resume, max open risk** as hard gates on new entries. |
| `autooptimize` 18:00 | **Repoint or freeze** | If kept, must optimize against `engine/backtest_fast` (validated), not `services/backtest_engine`. **Recommendation: freeze/deprioritize** — research concluded selection & param-tuning carry little edge and overfitting risk is high (handoff §5). |
| `shadow_portfolio` | **Keep** | Already engine-shaped (`composite_score`, `rr_ratio`, `regime`). Use as the live-vs-shadow reconciliation surface. |
| `learning_agent`, `cio_agent` | **Keep, re-source** | CIO brief should report v2 runtime metrics; learning agent post-mortems v2 trades. |

---

## 5. Schema changes (minimal, additive)

Persistence already fits the engine remarkably well (`scan_results` carries `avg_trp`,
`volume_ratio`, `stage`, `trigger_level`; `shadow_trades` carries `composite_score`,
`stop_price`, `rr_ratio`, `signal_type`, `regime`). **One gap is fatal and must be fixed:**

| Table | Add | Why |
|---|---|---|
| `trades` | **`current_stop`** (Numeric) | v2's stop **moves** (chandelier). Today only static write-once `sl_price` exists → **a trailing exit cannot be represented at all.** #1 blocker. |
| `trades` | **`highest_high`** (Numeric), **`atr_at_entry`**/running ATR | needed to compute the ratchet each day |
| `trades` | `signal_type`, `regime_at_entry`, `volume_ratio_at_entry`, `avg_trp_at_entry` | attribution; port from `shadow_trades` shape |
| `trades` | `strategy_version` (e.g. `v2`/`legacy`) | A/B and clean rollback |
| `simulation_trades` | `current_stop`, `highest_high` | paper parity with live (same gap today) |

No tables need deleting. No destructive migrations.

---

## 6. Phased rollout

### Phase 0 — Foundation (no live trading)
- [x] Extract `exit_service` (close-based 5×ATR chandelier) + `signal_service` (v2 entry,
      ≥2× vol gate + circuit-skip) into `backend/engine/runtime/`. *(risk_manager: TODO)*
- [x] **Parity harness PASSED** (`scripts/run_runtime_parity.py`): full universe, 1,272
      symbols, **293 v2 trades, 0 mismatches** — the runtime reproduces `backtest_fast`
      v2 trade-for-trade. **GATE GREEN.**
- [x] **Typed config** (`runtime/config.py`): `StrategyParams`/`RiskParams`, frozen &
      versioned (`v2`), with the tiered-slippage model; `signal_service`/`exit_service`
      now read it — **no magic numbers**. Parity **re-confirmed 293/293** post-refactor.
- [x] **Extracted `risk_manager`** (`runtime/risk_manager.py`): `simulate_portfolio` +
      live primitives (`position_size`, `bear_multiplier`, `update_halt`). Portfolio
      parity (`scripts/run_portfolio_parity.py`) **curve-for-curve, 0/2503 mismatches**,
      headline reproduced (26.5% / 14.8% / 1.79 / 19.5%). `run_v2_deployable_tiers.py`
      now calls it (inline copy deleted).
- [x] **Trailing-stop schema** (§5): `current_stop`/`highest_high`/`atr_at_entry` +
      attribution + `strategy_version` on `trades` (+ trail trio on `simulation_trades`);
      idempotent migration `scripts/migrate_add_v2_trail_columns.py`.
- [x] **Kite `bars`/`index_bars` ingest** (`backend/engine/market_store.py` +
      `scripts/ingest_kite_daily.py`): incremental, leakage-safe, retry/backoff; the
      engine's `load_bars`/`load_regime` read it back identically (8 tests, fake adapter).
      `build_cache_kite.py` now shares the same fetch code. *(Retiring the yfinance scan
      feed is the Phase-1 scanner rewire.)*

> **Phase 0 complete.** The validated brain is extracted, config-driven, and parity-gated
> (per-symbol + portfolio); the trailing-stop blocker is cleared; the Kite feed is stood up.

### Phase 1 — Live paper-trading on the validated engine (handoff backlog #1)
- [x] **Runtime bridge** (`backend/services/strategy_runtime.py`): the ONE seam the live
      jobs call — `scan_symbol`/`scan_universe` (→ signal_service), `evaluate_live_entry`
      (trigger-break + **projected last-30-min volume gate** + `live_position_size`),
      `open_trail`/`trail_from_db` + `morning_gap_exit`/`eod_exit` (→ exit_service). Pure
      (no FastAPI); 16 unit tests. Encodes the two live decisions (volume projection; exit
      once-daily-close + 09:15 gap-check).
- [~] **v2 scanner built & tested** (`scanner_engine.run_v2_scan` + runtime `detect_setup`
      / `setup_at` + bridge `scan_universe`): reads the Kite bars store, emits READY
      `ScanResult` rows for true v2 setups ≥ the liquidity floor; PPC/NPC retained as
      non-gating labels. Verified against the real cache (`test_scanner_v2`). *Pending: wire
      the `daily_scanner` job (main.py) to call it instead of `run_all_scans`.*
- [ ] Re-point `entry_monitor` (last 30 min) to `evaluate_live_entry`; persist the trail.
- [~] **v2 exit job built & tested** (`exit_runtime.run_eod_exits` + `run_morning_gap_exits`):
      close-based 5×ATR chandelier on open trades, persists the ratcheting stop to the new
      `current_stop`/`highest_high` columns, self-heals legacy trades. In-memory-DB tested.
      *Pending: wire `exit_monitor` to it (once-daily post-close + 09:15) and delete the
      2R/4R/8R/12R ladder + 2-min intraday-touch loop.*
- [ ] Promote `risk_guardian` to enforce caps / DD halt / bear-sizing (via risk_manager).
- [ ] Wire Telegram entry/exit + brief; run in SHADOW, then paper.
- [ ] Run the full pipeline of §3 in **paper mode** on live Kite data: scan → watchlist →
      last-30-min entry → `risk_manager` sizing → **close-based chandelier** exit
      monitoring → `trades`/`partial_exits` → Telegram.
- [ ] 10–15 live sessions. **Reconcile real fills vs backtest assumptions** (esp. thin
      names — the +178R ASAL winner was an illiquid micro-cap that may not fill at size).
- [ ] Daily live-vs-shadow reconciliation; investigate any divergence > tolerance.
- [ ] **No real orders.** Exit: paper Calmar/DD/win-rate within the backtest's band.

### Phase 2 — Dhan live with safeguards
- [ ] Order execution via **Kite Connect (Zerodha)** — the *same* provider as the data
      feed, so feed + execution share one auth/session. (`services/dhan_client.py` and the
      `/webhook/dhan` stub are now dead code — Dhan is not used.)
- [ ] Start on the **top-500 liquidity tier**, reduced RPT, small capital.
- [ ] Hard gates: 15-pos cap, 15% DD breaker, bear-sizing, max open risk, **kill-switch**,
      earnings/announcement blackout, reconciled cost model (`costs.py` flags FY25-26
      rates need a real Zerodha/Dhan contract-note check before go-live).
- [ ] Daily P&L + position reconciliation vs broker statements.

---

## 7. Riskiest assumptions (backtest daily-bars vs live intraday reality)

1. **Close-based stop needs the *official* close, not a snapshot.** The whole edge
   depends on exiting only on a confirmed daily close below the stop (or gap-down open).
   If the live exit job keeps using yfinance intraday snapshots it reintroduces the
   78%-premature-exit / −10pt-win-rate failure. **Exit decisions must run once, on the
   official EOD bar.** (Job-semantics change, §4 `exit_monitor`.)
2. **Entry fill vs the daily-bar assumption.** Backtest fills at
   `max(trigger, open) × (1+10bps)` on the daily breakout bar. Live enters intraday in the
   last 30 min — the realized price (esp. on gap-ups) can differ. Reconcile in Phase 1.
3. **The ≥2× volume gate can only be *finalized* at close**, but entry is in the last 30
   min. Either confirm with EOD-projected volume in the last 30 min, or enter next day on
   confirmed volume. Pick one and measure the slippage of that choice vs the backtest
   (which sees full-day volume). **Genuinely unresolved.**
4. **Thin-name capacity.** Tiered 10–100 bps slippage is an assumption; the biggest
   winners were illiquid. Real impact cost at size may erase them. Mitigation: top-500
   tier live; measure fills in Phase 1.
5. **Circuit-locked breakouts** (upper-band, no sellers) are *skipped* in the backtest;
   live must detect and not chase them (logic exists in `backtest_fast`, must move to the
   live entry path).
6. **Survivorship bias.** The universe = symbols with data *today*; live includes
   future-delisted names → backtest returns are inflated (handoff backlog #2, unquantified).
7. **Data-adjustment parity.** The original phantom-loss bug was unadjusted prices. Live
   **must** use the same Kite-adjusted feed as the backtest; yfinance vs Kite adjustment
   differences will manufacture false signals.
8. **Momentum-rank selection needs 252 bars**; the current 9-month live window is too
   short. (Selection carries no edge, but determinism matters when signals > slots.)
9. **Cost model reconciliation** before go-live (`costs.py` says so explicitly). v2 has
   **no partial exits**, which actually *simplifies* live costs vs the legacy ladder.

---

## 8. Open decisions (need a human call before building)

1. ~~Data feed & broker~~ **DECIDED:** feed **and** execution both on **Kite/Zerodha**
   (matches the backtest; one provider, one session). Dhan is not used.
2. **Liquidity tier for go-live:** full universe (24.5% CAGR, small account) vs **top-500**
   (18% CAGR, best Calmar, scalable)? Recommend top-500 for real money.
3. **Legacy PPC/NPC scanners:** delete, or retain as non-gating labels alongside v2?
4. **AutoOptimize:** freeze (recommended) or repoint at the validated backtester?
5. ~~`exit_monitor` cadence~~ **DECIDED:** pure **once-daily post-close** evaluation
   (`eod_exit`) + a **09:15 gap-down check** (`morning_gap_exit`). The 2-min intraday
   loop is removed (it caused the 78%-premature-exit failure v2 was built to avoid).
6. ~~Entry volume-gate timing~~ **DECIDED:** since the >=2x gate finalises only at the
   close but entries fire in the last 30 min, **project full-day volume** from
   volume-so-far and require the projection >= 2x the 50-day average (`breakout_volume_ok`).
   Reconcile the projection vs realised full-day volume in the Phase-1 paper run.

---

## 9. Suggested build order (when we say go)

1. `engine/runtime/` extraction + v2 upgrade + trailing-stop schema. *(Phase 0)*
2. Parity harness — **gate**. *(Phase 0)*
3. Kite `bars`/`index_bars` ingest. *(Phase 0)*
4. Re-point `daily_scanner` + watchlist to the runtime. *(Phase 1)*
5. Re-point entry (`entry_monitor`) + sizing (`risk_manager`, RPT 0.35, caps). *(Phase 1)*
6. Replace exit logic with close-based `exit_service`; change `exit_monitor` semantics. *(Phase 1)*
7. Promote `risk_guardian` to enforcer (caps, DD breaker, bear-sizing). *(Phase 1)*
8. Wire Telegram entry/exit alerts. *(Phase 1)*
9. Paper run 10–15 sessions + reconciliation. *(Phase 1)*
10. `BrokerClient`/Dhan + safeguards + kill-switch. *(Phase 2)*

---

*Source audits: live scan path, sizing/exit path, autopilot/alerts/scheduler, engine
contract, DB schema + routers — all read-only, cited inline above. Engine entry points:
`engine/production_signal.py`, `engine/backtest_fast.py::_fast_simulate`,
`engine/signals.py::classify_watch_state`, `engine/regime.py::load_regime`,
`engine/precompute.py::precompute_features`, `engine/kite_data.py::Bar`. Live core:
`services/scanner_engine.py`, `services/paper_trading.py`, `services/price_monitor*.py`,
`services/autopilot.py`, `services/position_calculator.py`, `backend/main.py::_setup_scheduler`,
`backend/tables.py`.*
