"""
autooptimize_scoring.py -- Composite scoring and backtest evaluation for AutoOptimize.

Scoring formula:
  composite_score = expectancy * sqrt(trade_count) * (1 - max_drawdown_pct)

Penalties:
  - score halved if max_drawdown > 15%
  - score = 0 if trade_count < MIN_TRADE_COUNT (8)
"""

from __future__ import annotations

import logging
import math
import time
from datetime import date, datetime, timedelta
from typing import Any

from backend.database import (
    SessionLocal,
    SimulationRun,
    SimulationTrade,
)
# AutoOptimize is frozen for v2 rollout — backtest_engine removed.
# Re-enable only when a versioned research config is ready.
def _bt_run_backtest(*args, **kwargs):
    raise NotImplementedError("AutoOptimize is frozen — backtest_engine has been removed.")

logger = logging.getLogger("autooptimize")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BACKTEST_WINDOW_CALENDAR_DAYS = 90       # ~60 trading days
BACKTEST_STARTING_CAPITAL = 1_000_000.0  # 10 lakh INR
BACKTEST_RPT_PCT = 0.50                  # default RPT
BACKTEST_POLL_INTERVAL_SEC = 5           # seconds between completion polls
BACKTEST_MAX_WAIT_SEC = 600              # 10 min max wait per backtest
MIN_TRADE_COUNT = 8                      # below this, composite_score = 0
MAX_DRAWDOWN_PENALTY_THRESHOLD = 0.15    # halve score above 15% drawdown


# ===========================================================================
# 1. COMPOSITE SCORE
# ===========================================================================

def compute_composite_score(
    run: SimulationRun, trades: list[SimulationTrade]
) -> dict[str, float]:
    """
    Compute the composite score from a completed backtest run.

    composite_score = expectancy * sqrt(trade_count) * (1 - max_drawdown_pct)

    where:
      expectancy = (win_rate * avg_win_R) - (loss_rate * avg_loss_R)
      PENALTY: score halved if max_drawdown > 15%
      PENALTY: score = 0 if trade_count < MIN_TRADE_COUNT

    All DB values are cast to float to avoid Decimal/float TypeError.
    """
    trade_count = len(trades)

    if trade_count < MIN_TRADE_COUNT:
        return {
            "composite_score": 0.0,
            "expectancy": 0.0,
            "trade_count": trade_count,
            "max_drawdown_pct": float(run.max_drawdown_pct or 0),
            "win_rate": 0.0,
        }

    wins = [t for t in trades if float(t.r_multiple or 0) > 0]
    losses = [t for t in trades if float(t.r_multiple or 0) <= 0]

    win_rate = len(wins) / trade_count
    loss_rate = 1.0 - win_rate

    avg_win_r = (
        sum(float(t.r_multiple) for t in wins if t.r_multiple is not None) / len(wins)
        if wins
        else 0.0
    )
    avg_loss_r = (
        abs(sum(float(t.r_multiple) for t in losses if t.r_multiple is not None) / len(losses))
        if losses
        else 0.0
    )

    expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)

    # max_drawdown_pct from backtest_engine is stored as percentage (0-100)
    raw_dd = float(run.max_drawdown_pct or 0)
    max_dd = raw_dd / 100.0 if raw_dd > 1.0 else raw_dd

    score = expectancy * math.sqrt(trade_count) * (1.0 - max_dd)

    if max_dd > MAX_DRAWDOWN_PENALTY_THRESHOLD:
        score *= 0.5

    return {
        "composite_score": round(score, 6),
        "expectancy": round(expectancy, 4),
        "trade_count": trade_count,
        "max_drawdown_pct": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
    }


# ===========================================================================
# 2. BACKTEST ADAPTER
# ===========================================================================

def _wait_for_backtest(
    run_id: int, timeout_sec: int = BACKTEST_MAX_WAIT_SEC
) -> SimulationRun:
    """
    Poll the database until the backtest run reaches COMPLETED or FAILED.
    The backtest_engine runs in a background thread, so we poll.
    Returns the refreshed SimulationRun row.
    Raises RuntimeError on timeout or failure.
    """
    elapsed = 0
    while elapsed < timeout_sec:
        db = SessionLocal()
        try:
            run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
            if run is None:
                raise RuntimeError(f"Backtest run {run_id} not found in database")
            if run.status == "COMPLETED":
                return run
            if run.status == "FAILED":
                raise RuntimeError(
                    f"Backtest run {run_id} failed: {run.error_message or 'unknown error'}"
                )
        finally:
            db.close()

        time.sleep(BACKTEST_POLL_INTERVAL_SEC)
        elapsed += BACKTEST_POLL_INTERVAL_SEC

    raise RuntimeError(f"Backtest run {run_id} timed out after {timeout_sec}s")


def run_backtest_and_score() -> tuple[float, dict[str, Any]]:
    """
    Launch a backtest for the standard window, wait for completion,
    and return (composite_score, full_metrics_dict).
    """
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=BACKTEST_WINDOW_CALENDAR_DAYS)

    db = SessionLocal()
    try:
        sim_run = _bt_run_backtest(
            db=db,
            start_date=start_dt,
            end_date=end_dt,
            starting_capital=BACKTEST_STARTING_CAPITAL,
            rpt_pct=BACKTEST_RPT_PCT,
            name=f"autooptimize_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
        run_id = sim_run.id
    finally:
        db.close()

    # Poll until complete
    _wait_for_backtest(run_id)

    # Fetch trades for scoring
    db = SessionLocal()
    try:
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        trades = (
            db.query(SimulationTrade)
            .filter(SimulationTrade.run_id == run_id)
            .all()
        )
        metrics = compute_composite_score(run, trades)
    finally:
        db.close()

    return metrics["composite_score"], metrics
