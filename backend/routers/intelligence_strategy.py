"""
Intelligence Strategy API router -- strategy parameter inspection and learning progress.

Endpoints:
  /api/intelligence/strategy/parameters  — Live parameter values and bounds
  /api/intelligence/learning-progress    — Full learning loop dashboard data
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


# ── Strategy Parameters ─────────────────────────────────────────────


@router.get("/strategy/parameters")
async def get_parameters() -> dict:
    """Get current strategy parameters and bounds."""
    from backend.intelligence.strategy import BOUNDS, PARAMETERS, validate_parameters

    violations = validate_parameters()

    return {
        "parameters": PARAMETERS,
        "bounds": {k: list(v) for k, v in BOUNDS.items()},
        "valid": len(violations) == 0,
        "violations": violations,
    }


# ── Learning Progress (Frontend Dashboard) ────────────────────────


@router.get("/learning-progress")
async def learning_progress() -> dict:
    """
    Comprehensive learning loop status for the frontend dashboard.

    Returns:
      - loop_status: is the feedback loop actually closed?
      - parameter_trajectories: how each param evolved over experiments
      - experiment_timeline: chronological outcomes
      - regime_history: recent regime classifications
      - learning_velocity: how fast the system is improving
    """
    from backend.intelligence.autooptimize import get_history, get_history_summary
    from backend.intelligence.parameter_banks import get_active_parameters, get_bank_info
    from backend.intelligence.regime_classifier import get_latest_regime
    from backend.intelligence.strategy import BOUNDS, PARAMETERS

    rows = get_history()
    summary = get_history_summary()
    regime_info = get_latest_regime()
    regime = regime_info.get("regime", "RANGING_QUIET")
    effective_params = get_active_parameters(regime)
    bank_info = get_bank_info()

    # Build parameter trajectories: for each parameter, track its value over time
    param_trajectories: dict[str, list[dict]] = {}
    for row in rows:
        param_name = row.get("parameter", "")
        if not param_name:
            continue
        if param_name not in param_trajectories:
            param_trajectories[param_name] = []

        param_trajectories[param_name].append({
            "timestamp": row.get("timestamp"),
            "old_value": _safe_score(row.get("old_value")),
            "new_value": _safe_score(row.get("new_value")),
            "outcome": row.get("outcome"),
            "old_score": _safe_score(row.get("old_score")),
            "new_score": _safe_score(row.get("new_score")),
            "hypothesis": row.get("hypothesis", ""),
        })

    # Current values with bounds context
    param_details = {}
    for key, value in PARAMETERS.items():
        lo, hi = BOUNDS.get(key, (0, 0))
        effective_value = effective_params.get(key, value)
        experiment_count = len(param_trajectories.get(key, []))
        keep_count = sum(
            1 for t in param_trajectories.get(key, [])
            if t["outcome"] == "KEEP"
        )
        param_details[key] = {
            "base_value": value,
            "effective_value": effective_value,
            "regime_adjusted": effective_value != value,
            "bound_low": lo,
            "bound_high": hi,
            "position_in_range": round((value - lo) / (hi - lo), 3) if hi > lo else 0.5,
            "experiments_run": experiment_count,
            "improvements": keep_count,
        }

    # Experiment timeline (last 50)
    timeline = [
        {
            "timestamp": r.get("timestamp"),
            "parameter": r.get("parameter"),
            "outcome": r.get("outcome"),
            "score_delta": round(
                _safe_score(r.get("new_score")) - _safe_score(r.get("old_score")),
                4,
            ) if r.get("new_score") and r.get("old_score") else None,
        }
        for r in rows[-50:]
    ]

    # Learning velocity: improvement rate in recent vs older experiments
    recent_window = 10
    recent = rows[-recent_window:] if len(rows) >= recent_window else rows
    older = rows[:-recent_window] if len(rows) > recent_window else []

    recent_keep = sum(1 for r in recent if r.get("outcome") == "KEEP")
    older_keep = sum(1 for r in older if r.get("outcome") == "KEEP")

    velocity = {
        "recent_keep_rate": round(recent_keep / len(recent) * 100, 1) if recent else 0,
        "older_keep_rate": round(older_keep / len(older) * 100, 1) if older else None,
        "trend": (
            "improving" if older and recent_keep / max(len(recent), 1) > older_keep / max(len(older), 1)
            else "stable" if not older
            else "plateau"
        ),
        "total_experiments": len(rows),
    }

    # Loop health check
    loop_closed = True
    loop_issues: list[str] = []
    if not rows:
        loop_closed = False
        loop_issues.append("No experiments have run yet")
    if summary.get("keep_rate_pct", 0) == 0 and len(rows) > 5:
        loop_issues.append("No experiments have been kept — learning may be stuck")

    return {
        "loop_status": {
            "closed": loop_closed,
            "issues": loop_issues,
            "description": (
                "The learning loop is active: AutoOptimize runs experiments → "
                "updates strategy.py PARAMETERS → signal_agent and backtest_engine "
                "read these parameters for filtering and scoring → results feed back "
                "into the next experiment cycle."
                if loop_closed else
                "The learning loop has not started yet. Start AutoOptimize to begin."
            ),
        },
        "current_regime": regime_info,
        "regime_banks": bank_info,
        "parameters": param_details,
        "experiment_summary": summary,
        "experiment_timeline": timeline,
        "learning_velocity": velocity,
    }


def _safe_score(val: str | None) -> float:
    """Convert experiment score string to float for display. Not for financial math."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
