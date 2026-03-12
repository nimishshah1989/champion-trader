from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import SimulationRun, SimulationTrade, get_db
from backend.models.simulation import (
    BacktestRequest,
    PaperStartRequest,
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
