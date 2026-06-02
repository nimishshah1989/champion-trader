from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import ScanResult, get_db
from backend.models.scan_result import ScanRequest, ScanResultResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scanner", tags=["Scanner"])


@router.post("/run", response_model=list[ScanResultResponse])
def run_scan(request: ScanRequest, db: Session = Depends(get_db)):
    """Run the validated v2 setup scan and return the persisted READY rows.

    This is the SAME brain the daily_scanner cron runs (live_jobs.run_daily_scan):
    it reads the Kite-adjusted bar store through the parity-proven runtime, writes
    scan_type="V2" ScanResult rows, and populates the watchlist. The legacy
    PPC/NPC/Contraction scanners survive only as non-gating labels, so the request's
    scan_type is accepted for back-compat but ignored — there is one validated setup
    type now. Sync def: the full-universe scan is blocking, so FastAPI runs it in a
    worker thread instead of stalling the event loop.
    """
    scan_date = request.date or date.today()
    logger.info(f"Running v2 setup scan for {scan_date}")

    from backend.services.live_jobs import run_daily_scan

    result = run_daily_scan(scan_date)
    if "error" in result:
        logger.error(f"v2 scan failed: {result['error']}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {result['error']}")

    return (
        db.query(ScanResult)
        .filter(ScanResult.scan_date == scan_date, ScanResult.scan_type == "V2")
        .order_by(ScanResult.symbol)
        .all()
    )


@router.get("/results", response_model=list[ScanResultResponse])
def get_scan_results(
    scan_date: Optional[date] = Query(None),
    scan_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get scan results for a given date and/or type."""
    query = db.query(ScanResult)
    if scan_date:
        query = query.filter(ScanResult.scan_date == scan_date)
    if scan_type:
        query = query.filter(ScanResult.scan_type == scan_type.upper())
    return query.order_by(desc(ScanResult.scan_date)).all()


@router.get("/results/latest", response_model=list[ScanResultResponse])
def get_latest_results(db: Session = Depends(get_db)):
    """Get the most recent scan results grouped by type."""
    latest = db.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
    if not latest:
        return []
    return (
        db.query(ScanResult)
        .filter(ScanResult.scan_date == latest[0])
        .all()
    )
