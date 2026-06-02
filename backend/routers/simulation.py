from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import SimulationRun, SimulationTrade, get_db
from backend.models.simulation import (
    BacktestRequest,
    PaperStartRequest,
    RSBacktestRequest,
    RSBacktestResponse,
    SimulationRunResponse,
    SimulationRunWithTrades,
    SimulationTradeResponse,
)
from backend.services.backtest_engine import cleanup_stuck_backtests, run_backtest
from backend.services.paper_trading import (
    get_paper_status,
    process_paper_day,
    start_paper_session,
    stop_paper_session,
)
from backend.services.rs_backtest_engine import run_rs_backtest

router = APIRouter(prefix="/simulation", tags=["Simulation"])


@router.post("/backtest", response_model=SimulationRunResponse)
def create_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    """Run a historical backtest over the given date range."""
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    result = run_backtest(
        db=db,
        start_date=req.start_date,
        end_date=req.end_date,
        starting_capital=req.starting_capital,
        rpt_pct=req.rpt_pct,
        name=req.name,
    )
    return result


@router.get("/backtest/{run_id}", response_model=SimulationRunWithTrades)
def get_backtest_result(run_id: int, db: Session = Depends(get_db)):
    """Get backtest results including trade log."""
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    trades = (
        db.query(SimulationTrade)
        .filter(SimulationTrade.run_id == run_id)
        .order_by(SimulationTrade.entry_date)
        .all()
    )

    result = SimulationRunWithTrades.model_validate(run)
    result.trades = [SimulationTradeResponse.model_validate(t) for t in trades]
    return result


@router.post("/paper/start", response_model=SimulationRunResponse)
def start_paper(req: PaperStartRequest, db: Session = Depends(get_db)):
    """Start a new paper trading session."""
    # Check if there's already an active paper session
    active = (
        db.query(SimulationRun)
        .filter(SimulationRun.run_type == "PAPER", SimulationRun.status == "ACTIVE")
        .first()
    )
    if active:
        raise HTTPException(
            status_code=400,
            detail=f"Already have an active paper session (id={active.id}). Stop it first.",
        )

    result = start_paper_session(
        db=db,
        starting_capital=req.starting_capital,
        rpt_pct=req.rpt_pct,
        name=req.name,
    )
    return result


@router.post("/paper/{run_id}/process")
def process_paper(run_id: int, db: Session = Depends(get_db)):
    """Process today's paper trading — check exits and new entries."""
    try:
        result = process_paper_day(db, run_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/paper/{run_id}", response_model=SimulationRunWithTrades)
def get_paper_portfolio(run_id: int, db: Session = Depends(get_db)):
    """Get current paper trading portfolio status."""
    try:
        status = get_paper_status(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    run = status["run"]
    all_trades = status["open_trades"] + status["closed_trades"]

    result = SimulationRunWithTrades.model_validate(run)
    result.trades = [SimulationTradeResponse.model_validate(t) for t in all_trades]
    return result


@router.post("/paper/{run_id}/stop", response_model=SimulationRunResponse)
def stop_paper(run_id: int, db: Session = Depends(get_db)):
    """Stop paper session — close all virtual positions at current prices."""
    try:
        result = stop_paper_session(db, run_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs", response_model=list[SimulationRunResponse])
def list_runs(
    run_type: Optional[str] = Query(None, description="BACKTEST or PAPER"),
    db: Session = Depends(get_db),
):
    """List all simulation runs."""
    query = db.query(SimulationRun)
    if run_type:
        query = query.filter(SimulationRun.run_type == run_type.upper())
    runs = query.order_by(SimulationRun.created_at.desc()).all()
    return runs


@router.get("/backtest/{run_id}/progress")
def get_backtest_progress(run_id: int, db: Session = Depends(get_db)):
    """Get live progress for a running backtest.

    Returns phase (fetching/computing/scanning), progress percentage,
    and current date being processed.
    """
    import json as _json

    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    status = run.status.upper() if run.status else "UNKNOWN"

    # If completed or failed, return final state
    if status in ("COMPLETED", "FAILED", "ERROR"):
        return {
            "run_id": run_id,
            "status": status,
            "phase": "done" if status == "COMPLETED" else "failed",
            "progress_pct": 100 if status == "COMPLETED" else 0,
            "error_message": run.error_message if status != "COMPLETED" else None,
        }

    # Try to parse progress from error_message (used as progress storage during RUNNING)
    progress = {"phase": "initializing", "progress_pct": 0}
    if run.error_message:
        try:
            progress = _json.loads(run.error_message)
        except (_json.JSONDecodeError, TypeError):
            pass

    return {
        "run_id": run_id,
        "status": status,
        **progress,
    }


@router.post("/rs-backtest", response_model=RSBacktestResponse)
def create_rs_backtest(req: RSBacktestRequest, db: Session = Depends(get_db)):
    """
    Launch all three RS crossover backtest scenarios simultaneously.

    Scenarios:
    - RS_ONLY: Buy/sell based solely on SMA20/SMA200 crossover of RS ratio (stock / Nifty 50)
    - DUAL_EITHER: Buy when both price AND RS crossovers are bullish; sell when EITHER reverses
    - DUAL_BOTH: Same dual buy; sell only when BOTH crossovers have reversed

    Returns run IDs for all three scenarios immediately (runs in background).
    Poll /simulation/backtest/{run_id}/progress to track status.
    """
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    runs = run_rs_backtest(
        db=db,
        start_date=req.start_date,
        end_date=req.end_date,
        starting_capital=float(req.starting_capital),
        rpt_pct=float(req.rpt_pct),
        stop_loss_pct=float(req.stop_loss_pct),
        max_positions=req.max_positions,
        name=req.name,
    )

    return RSBacktestResponse(
        rs_only_run_id=runs["RS_ONLY"].id,
        dual_either_run_id=runs["DUAL_EITHER"].id,
        dual_both_run_id=runs["DUAL_BOTH"].id,
        message=(
            f"RS backtest started for all 3 scenarios. "
            f"Run IDs: RS_ONLY={runs['RS_ONLY'].id}, "
            f"DUAL_EITHER={runs['DUAL_EITHER'].id}, "
            f"DUAL_BOTH={runs['DUAL_BOTH'].id}. "
            f"Poll /simulation/backtest/{{run_id}}/progress for status."
        ),
    )


@router.get("/rs-backtest/comparison")
def rs_backtest_comparison(
    rs_only_id: int = Query(..., description="Run ID for RS_ONLY scenario"),
    dual_either_id: int = Query(..., description="Run ID for DUAL_EITHER scenario"),
    dual_both_id: int = Query(..., description="Run ID for DUAL_BOTH scenario"),
    db: Session = Depends(get_db),
):
    """
    Side-by-side comparison of all three RS scenarios.
    Returns a structured summary table for easy comparison.
    """
    ids = {
        "RS_ONLY":     rs_only_id,
        "DUAL_EITHER": dual_either_id,
        "DUAL_BOTH":   dual_both_id,
    }
    comparison = {}
    for scenario, run_id in ids.items():
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} ({scenario}) not found")
        comparison[scenario] = {
            "run_id":           run.id,
            "status":           run.status,
            "total_trades":     run.total_trades,
            "win_rate_pct":     run.win_rate,
            "avg_win_pct":      run.avg_win_r,
            "avg_loss_pct":     run.avg_loss_r,
            "expectancy":       run.expectancy,
            "total_return_pct": run.total_return_pct,
            "arr_pct":          run.arr,
            "max_drawdown_pct": run.max_drawdown_pct,
            "final_capital":    float(run.final_capital) if run.final_capital else None,
            "total_pnl":        float(run.total_pnl) if run.total_pnl else None,
        }
    return {
        "comparison": comparison,
        "hypothesis": (
            "RS_ONLY = pure relative strength filter | "
            "DUAL_EITHER = dual entry, aggressive exit | "
            "DUAL_BOTH = dual entry, conservative exit"
        ),
    }


@router.post("/cleanup-stuck")
def cleanup_stuck(db: Session = Depends(get_db)):
    """Mark stuck RUNNING backtests as FAILED.

    Useful after server restarts when background threads were killed.
    """
    cleaned_ids = cleanup_stuck_backtests()
    return {
        "cleaned": len(cleaned_ids),
        "run_ids": cleaned_ids,
        "message": f"Cleaned up {len(cleaned_ids)} stuck backtests" if cleaned_ids else "No stuck backtests found",
    }
