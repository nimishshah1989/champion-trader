"""
Intelligence API router -- all CTS Intelligence layer endpoints.

Endpoints:
  /api/intelligence/optimize/*     — AutoOptimize loop control and history
  /api/intelligence/regime*        — Market regime classification
  /api/intelligence/brief*         — CIO Daily Brief
  /api/intelligence/approve|skip   — Human setup approval
  /api/intelligence/shadow         — Shadow vs live portfolio
  /api/intelligence/attribution    — Signal win rate attribution
  /api/intelligence/rag/*          — RAG memory queries and stats
  /api/intelligence/risk/*         — Risk Guardian status and freeze control
  /api/intelligence/strategy/*     — Live parameter inspection

All intelligence module imports are LAZY (inside handler functions)
to avoid circular import issues between intelligence submodules.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


# ── AutoOptimize Endpoints ──────────────────────────────────────────


@router.post("/optimize/start")
async def start_optimize():
    """Manually start the AutoOptimize loop."""
    from backend.intelligence.autooptimize import get_status, start_loop_background

    status = get_status()
    if status.get("running"):
        raise HTTPException(
            status_code=400,
            detail="AutoOptimize is already running",
        )

    start_loop_background()
    return {
        "status": "started",
        "message": "AutoOptimize loop started in background",
    }


@router.post("/optimize/stop")
async def stop_optimize():
    """Manually stop the AutoOptimize loop."""
    from backend.intelligence.autooptimize import stop_loop

    stop_loop()
    return {
        "status": "stopping",
        "message": "Stop signal sent -- will halt after current experiment",
    }


@router.get("/optimize/status")
async def optimize_status():
    """Get current AutoOptimize status."""
    from backend.intelligence.autooptimize import get_status

    return get_status()


@router.get("/optimize/history")
async def optimize_history():
    """Get full AutoOptimize experiment history."""
    from backend.intelligence.autooptimize import get_history, get_history_summary

    return {
        "experiments": get_history(),
        "summary": get_history_summary(),
    }


# ── Regime & Parameters ─────────────────────────────────────────────


@router.get("/regime")
async def get_regime():
    """Get current market regime and active parameter bank."""
    from backend.intelligence.parameter_banks import get_bank_info
    from backend.intelligence.regime_classifier import get_latest_regime

    regime = get_latest_regime()
    banks = get_bank_info()

    return {
        "regime": regime,
        "parameter_banks": banks,
    }


@router.post("/regime/classify")
async def classify_now():
    """Run regime classification now (usually runs at 16:45 IST)."""
    from backend.intelligence.regime_classifier import classify_regime

    try:
        result = await classify_regime()
        return result
    except Exception as exc:
        logger.error(f"[API] POST /regime/classify failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Regime classification failed: {str(exc)}",
        )


# ── Daily Brief ──────────────────────────────────────────────────────


@router.get("/brief")
async def get_brief():
    """Get the latest CIO Daily Brief."""
    from backend.intelligence.cio_agent import get_latest_brief

    return get_latest_brief()


@router.post("/brief/generate")
async def generate_brief_now():
    """Generate a new Daily Brief (usually runs at 17:00 IST)."""
    from backend.intelligence.cio_agent import generate_brief

    try:
        result = await generate_brief()
        return result
    except Exception as exc:
        logger.error(f"[API] POST /brief/generate failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Brief generation failed: {str(exc)}",
        )


# ── Setup Approval ───────────────────────────────────────────────────

MAX_SETUP_LOOKUP = 10


@router.post("/approve/{symbol}")
async def approve_setup(symbol: str):
    """Human approves a setup from the Daily Brief."""
    from backend.intelligence.shadow_portfolio import track_setup
    from backend.intelligence.signal_agent import get_top_setups

    # Find the setup card for this symbol
    setups = await get_top_setups(top_n=MAX_SETUP_LOOKUP)
    matching = [s for s in setups if s["symbol"] == symbol]

    if not matching:
        raise HTTPException(
            status_code=404,
            detail=f"No setup found for {symbol}",
        )

    # Mark as approved in shadow portfolio
    await track_setup(matching[0], was_approved=True)

    return {
        "status": "approved",
        "symbol": symbol,
        "setup": matching[0],
        "message": f"Setup for {symbol} approved. Shadow trade recorded.",
    }


@router.post("/skip/{symbol}")
async def skip_setup(symbol: str):
    """Human skips a setup from the Daily Brief."""
    from backend.intelligence.shadow_portfolio import track_setup
    from backend.intelligence.signal_agent import get_top_setups

    setups = await get_top_setups(top_n=MAX_SETUP_LOOKUP)
    matching = [s for s in setups if s["symbol"] == symbol]

    if matching:
        await track_setup(matching[0], was_approved=False)

    return {
        "status": "skipped",
        "symbol": symbol,
        "message": f"Setup for {symbol} skipped. Shadow trade will still track it.",
    }


# ── Shadow Portfolio ─────────────────────────────────────────────────


@router.get("/shadow")
async def get_shadow():
    """Get shadow vs live portfolio comparison."""
    from backend.intelligence.shadow_portfolio import get_shadow_comparison

    return get_shadow_comparison()


# ── Signal Attribution ───────────────────────────────────────────────


@router.get("/attribution")
async def get_attribution():
    """Get signal attribution table (win rate by signal type x regime)."""
    from backend.intelligence.learning_agent import get_attribution_table

    return {"attribution": get_attribution_table()}


# ── RAG Memory ───────────────────────────────────────────────────────

VALID_RAG_CORPORA = frozenset({"corpus_a", "corpus_b", "corpus_c"})
DEFAULT_RAG_TOP_K = 5


@router.get("/rag/stats")
async def rag_stats():
    """Get document counts for all RAG corpora."""
    from backend.intelligence.rag_engine import get_corpus_stats

    return get_corpus_stats()


@router.post("/rag/query")
async def rag_query_endpoint(corpus: str, question: str, top_k: int = DEFAULT_RAG_TOP_K):
    """Query a RAG corpus with a natural language question."""
    from backend.intelligence.rag_engine import rag_query

    if corpus not in VALID_RAG_CORPORA:
        raise HTTPException(
            status_code=400,
            detail=f"corpus must be one of {sorted(VALID_RAG_CORPORA)}",
        )

    results = rag_query(question, corpus, top_k)
    return {
        "corpus": corpus,
        "question": question,
        "results": results,
    }


# ── Risk Guardian ────────────────────────────────────────────────────


@router.get("/risk/status")
async def risk_status():
    """Get Risk Guardian status including freeze state."""
    from backend.intelligence.portfolio_math import calculate_open_risk
    from backend.intelligence.risk_guardian import is_frozen
    from backend.database import SessionLocal, Trade

    db = SessionLocal()
    try:
        open_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
            .all()
        )

        positions = [
            {
                "symbol": t.symbol,
                "remaining_qty": t.remaining_qty,
                "avg_entry_price": t.avg_entry_price,
                "stop_loss": t.sl_price,
            }
            for t in open_trades
        ]

        risk = calculate_open_risk(positions, settings.default_account_value)

        return {
            "frozen": is_frozen(),
            "open_positions": len(open_trades),
            "risk": risk,
        }
    finally:
        db.close()


@router.post("/risk/unfreeze")
async def unfreeze_risk():
    """Manually lift the entry freeze."""
    from backend.intelligence.risk_guardian import unfreeze

    unfreeze()
    return {
        "status": "unfrozen",
        "message": "Entry freeze lifted",
    }


# ── Strategy Parameters ─────────────────────────────────────────────


@router.get("/strategy/parameters")
async def get_parameters():
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
async def learning_progress():
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
            "old_value": _safe_float(row.get("old_value")),
            "new_value": _safe_float(row.get("new_value")),
            "outcome": row.get("outcome"),
            "old_score": _safe_float(row.get("old_score")),
            "new_score": _safe_float(row.get("new_score")),
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
                _safe_float(r.get("new_score")) - _safe_float(r.get("old_score")),
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
    loop_issues = []
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


def _safe_float(val: str | None) -> float:
    """Convert string to float safely, returning 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
