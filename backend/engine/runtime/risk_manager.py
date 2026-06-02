"""Portfolio risk overlay — the validated v2 sizing, caps, bear-sizing & drawdown breaker.

Until now this lived ONLY as a `portfolio()` function copy-pasted into ~10 research
scripts (`run_v2_deployable_tiers.py`, `run_track3_volume.py`, ...). That duplication is
exactly the drift ARCHITECTURE.md forbids. It lives here now, once, PURE: it takes data
(planned trades + precomputed lookups + RiskParams) and returns an equity curve — no DB,
no network, no clock.

The same primitives the backtest overlay uses are exposed for the LIVE path:
  * position_size  — RPT sizing (entry_monitor sizes a fill with this)
  * bear_multiplier — 1.0 in a bull regime, RiskParams.bear_frac in a bear regime
  * update_halt    — the 15%/7.5% drawdown circuit-breaker state machine (risk_guardian)
  * simulate_portfolio — the full day-by-day overlay (backtest + the portfolio-parity gate)

`simulate_portfolio` is byte-identical to the research `portfolio()` it replaces; the
equivalence is enforced by `scripts/run_portfolio_parity.py`.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Mapping, Protocol, Sequence

from backend.engine.costs import CostModel
from backend.engine.runtime.config import RISK_V2, RiskParams

START_CAPITAL = Decimal("100000")
_MISSING_SCORE = -1e9   # candidates without a momentum score sort last (deterministic)


class TradeLike(Protocol):
    """The planned-trade contract the overlay consumes (RawTrade satisfies it)."""

    symbol: str
    entry_date: date
    exit_date: date
    entry: Decimal
    exit: Decimal
    stopdist: Decimal


def position_size(equity: Decimal, stopdist: Decimal, *, rpt_pct: float, bear_mult: Decimal) -> int:
    """Shares to buy: risk `rpt_pct`% of equity over the 1R stop distance, scaled by bear_mult.

    Truncates toward zero (never over-risk). Returns 0 for a non-positive stop distance.
    """
    if stopdist <= 0:
        return 0
    return int((equity * Decimal(str(rpt_pct)) * bear_mult / Decimal(100)) / stopdist)


def bear_multiplier(regime_on_today: bool, params: RiskParams = RISK_V2) -> Decimal:
    """Full size in a bull regime (index > rising N-DMA); quarter-size in a bear regime."""
    return Decimal("1.0") if regime_on_today else params.bear_frac


def update_halt(halted: bool, equity: float, peak: float, params: RiskParams = RISK_V2) -> bool:
    """Drawdown circuit-breaker: halt new entries below -dd_halt; resume within -dd_resume."""
    if equity < peak * (1 - params.dd_halt):
        return True
    if equity > peak * (1 - params.dd_resume):
        return False
    return halted


def _daily_yield_factor(annual_yield: float) -> Decimal:
    """Idle cash compounds at `annual_yield`, accrued daily over 252 sessions."""
    return Decimal(1 + ((1 + annual_yield) ** (1 / 252) - 1))


def simulate_portfolio(
    trades: Sequence[TradeLike],
    calendar: Sequence[date],
    *,
    params: RiskParams = RISK_V2,
    regime_on: Mapping[date, bool],
    momentum_score: Mapping[tuple[str, date], float],
    close_on: Mapping[str, Mapping[date, Decimal]],
    start_capital: Decimal = START_CAPITAL,
    cost_model: CostModel = CostModel(),
) -> list[tuple[date, float]]:
    """Run the v2 portfolio overlay day-by-day; return the equity curve [(date, equity)].

    Inputs are pure data:
      * trades        — the per-symbol v2 entries/exits (from the validated engine).
      * calendar      — the trading dates to walk, in order.
      * regime_on[d]  — True when the index is above its rising N-DMA (bull) on day d.
      * momentum_score[(symbol, entry_date)] — for deterministic same-day tie-breaking.
      * close_on[symbol][d] — daily close for marking open positions to market.
    """
    by_entry: dict[date, list[TradeLike]] = defaultdict(list)
    for t in trades:
        by_entry[t.entry_date].append(t)
    for d in by_entry:                       # deterministic same-day ordering (no edge; reproducibility)
        by_entry[d].sort(key=lambda t: momentum_score.get((t.symbol, t.entry_date), _MISSING_SCORE),
                         reverse=True)

    rpt = params.rpt_pct
    yield_factor = _daily_yield_factor(params.idle_yield)
    cash = start_capital
    open_pos: list[dict] = []
    curve: list[tuple[date, float]] = []
    peak = float(start_capital)
    halted = False

    for d in calendar:
        cash *= yield_factor                 # idle cash earns the daily yield
        # 1) realise exits scheduled for today (sell at the trade's exit price, net of costs)
        still: list[dict] = []
        for p in open_pos:
            if p["xd"] == d:
                proceeds = Decimal(p["sh"]) * p["xp"]
                cash += proceeds - cost_model.sell_costs(proceeds)
            else:
                still.append(p)
        open_pos = still
        # 2) mark open positions to today's close (hold last price on a no-bar day)
        for p in open_pos:
            p["px"] = close_on.get(p["s"], {}).get(d, p["px"])
        equity = cash + sum(Decimal(p["sh"]) * p["px"] for p in open_pos)
        # 3) drawdown circuit-breaker (on post-exit, pre-entry equity)
        peak = max(peak, float(equity))
        halted = update_halt(halted, float(equity), peak, params)
        # 4) new entries (if not halted), capped, sized, regime-scaled, cash-constrained
        if not halted:
            mult = bear_multiplier(regime_on.get(d, False), params)
            for t in by_entry.get(d, []):
                if len(open_pos) >= params.max_positions:
                    continue
                sh = position_size(equity, t.stopdist, rpt_pct=rpt, bear_mult=mult)
                if sh <= 0:
                    continue
                cost = Decimal(sh) * t.entry
                total = cost + cost_model.buy_costs(cost)
                if total > cash:
                    continue
                cash -= total
                open_pos.append({"s": t.symbol, "sh": sh, "xd": t.exit_date, "xp": t.exit, "px": t.entry})
        equity = cash + sum(Decimal(p["sh"]) * p["px"] for p in open_pos)
        curve.append((d, float(equity)))
    return curve
