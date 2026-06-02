# Phase A PRD — The Honest Evaluator

**Goal:** a *trustworthy* backtest engine on 10y Kite NIFTY 500 data — the shared
yardstick every later decision (calibration, go-live) is judged against. Pre-tax
R-multiples, full cost model, honest fills, zero look-ahead.

## Development loop (every module)
`PRD slice → unit tests (golden + property + leakage) → code → /code-review → fix → green → commit`
Money-critical code: `Decimal` only, two-way differential checks where feasible,
reconcile against ground truth (a real contract note / a second data source).

## Scope (Phase A)
| ID | Module | Validation |
|----|--------|------------|
| A1 | **Cost & tax model** (NSE delivery costs + STCG/LTCG) | golden vs hand-calc → reconcile to a real Zerodha contract note |
| A2 | Kite historical data adapter (point-in-time daily bars) | spot-check vs a 2nd source; leakage test |
| A3 | Signal engine (PPC/NPC/contraction/stage) — single source of truth, parameterized, per-stock-relative | golden bars; backtest==live uses same code |
| A4 | Fill engine (worse-of-stop-or-next-open + slippage) | crafted-bar tests (gap-down through stop, etc.) |
| A5 | Backtest loop + metrics (R, expectancy, **SQN**, Calmar, maxDD) | differential (compute two ways) |
| A6 | Validation harness + CI (pytest + mypy + ruff) | red CI blocks merge |

**Out of scope:** optimization/calibration (Phase B), live execution (Phase C).

## Done when
Cost model reconciled to a contract note · leakage test proves no future data is
used · all golden/property tests green · CI runs pytest+mypy+ruff · a sample
backtest runs on a handful of symbols.

## Iteration log
- **A1 (in progress):** cost & tax model — tests-first.
