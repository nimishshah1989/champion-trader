# Architecture & Engineering Standards

This system will keep evolving — new filters, better numbers, more predictability. These
standards exist so the codebase stays **clean as it grows**. The mess we audited (two
parallel strategies, scattered magic numbers, dead params, a second unvalidated
backtester) came from violating exactly these. **Every change follows them.**

---

## 1. Prime directive — one validated brain
- All strategy logic — entry, exit, sizing, risk — lives in **`backend/engine/runtime/`**
  and nowhere else. Services, scheduled jobs, the autopilot, the API, and the backtester
  all **call** it. There is never a second copy.
- The runtime is **proven equivalent to the backtest** by `scripts/run_runtime_parity.py`
  (trade-for-trade, currently 293/293). **Parity is a merge gate:** if a change breaks it,
  it's either a bug, or you deliberately move the golden baseline *with a written reason*.

## 2. Layering — pure core, imperative shell
Dependencies point **inward only**. Inner layers know nothing about outer ones.

```
  broker (Kite)  ─┐
  scheduler/jobs ─┤─►  services  (thin adapters / orchestration)
  API routers    ─┘          │ call
                             ▼
                    engine/runtime/   ← PURE: bars + params in, decisions out
                             ▲           (no I/O, no DB, no clock, no broker)
                    data ingest ─►  DB  (bars, index_bars, trades, …)
```

- **`engine/runtime/` is pure.** Functions take data (`Bar`s, params) and return
  decisions. No DB, no network, no `datetime.now()`, no printing. Purity is what makes it
  testable, parity-able, and shared by live + backtest. Keep it that way.
- **Services are thin.** They fetch data, call the runtime, persist, alert. If you find
  yourself writing a threshold or a trading rule in a service — stop; it belongs in the runtime.

## 3. Params are config, never magic numbers
- Every tunable (RPT, ≥2× volume, 5×ATR, min TRP, max positions, DD halt, liquidity
  floor) lives in **one typed, frozen config object** (`StrategyParams` / `RiskParams`),
  with defaults = the validated v2. No literal thresholds sprinkled through the code.
- Configs are **named & versioned** (`v2`, `v2.1`, …); trades persist `strategy_version`.
  This is how you sophisticate *safely*: clone a config, A/B it, roll back cleanly.
- **No dead params.** If a param isn't read by the code, delete it (we found 3 such).

## 4. Research and production are the same code
- The research scripts (`run_track*`, diagnostics) and the live system import the **same
  runtime**. A finding becomes production by **changing a param**, not by reimplementing.
  (Research living in `engine/` while live ran on `services/` is precisely how this drifted.)
- Any new edge follows the proven path: hypothesis → walk-forward A/B (TRAIN/TEST) →
  adopt **only** if it survives out-of-sample and shows a **plateau, not a peak** → flip the config.

## 5. Definition of done (every change)
1. Logic only in the runtime; services stayed thin.
2. Unit tests for new logic; **parity harness green** (or baseline moved with a reason).
3. No new magic numbers — params in the typed config.
4. Superseded code **deleted**, not left beside the new code.
5. `Decimal` for money; type hints; a docstring that states the *rule* it implements.
6. One focused commit; the diff reads like the surrounding code.

## 6. Where new code goes
| Adding… | Goes in… |
|---|---|
| a new entry filter / exit rule | `engine/runtime/` (+ a field in the config) |
| a portfolio / risk control | `engine/runtime/risk_manager.py` |
| a data source / ingest | data layer → writes `Bar`s into the DB |
| a broker action | the broker interface implementation (Kite) |
| a scheduled behaviour | a thin job that calls the runtime |
| an API / UI surface | a router → a service → the runtime |
| a research probe | `scripts/`, importing the runtime |

## 7. Delete, don't duplicate
When the runtime supersedes legacy logic (the old PPC/NPC scanner, the second
backtester, the yfinance feed, the Dhan stubs), **remove it** in the same change that
replaces it. Two ways to do one thing is how this codebase drifted in the first place.
Leave the tree smaller and clearer than you found it.

---

*Clean isn't a phase — it's the constraint that lets this system get more sophisticated
without rotting. If a change can't meet the Definition of Done, it isn't done.*
