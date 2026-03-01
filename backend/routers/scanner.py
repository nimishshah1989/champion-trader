from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from backend.database import ScanResult, get_db
from backend.models.scan_result import ScanRequest, ScanResultResponse
from backend.services.scanner_engine import (
    run_all_scans,
    run_contraction_scan,
    run_npc_scan,
    run_ppc_scan,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scanner", tags=["Scanner"])


def _save_results(db: Session, results: list[dict]) -> list[ScanResult]:
    """
    Save scan results to DB with upsert logic.
    Deletes existing results for the same (scan_date, symbol, scan_type)
    before inserting new ones.
    """
    saved: list[ScanResult] = []

    for result_dict in results:
        # Delete any existing result for this combo
        db.query(ScanResult).filter(
            and_(
                ScanResult.scan_date == result_dict["scan_date"],
                ScanResult.symbol == result_dict["symbol"],
                ScanResult.scan_type == result_dict["scan_type"],
            )
        ).delete()

        db_record = ScanResult(**result_dict)
        db.add(db_record)
        saved.append(db_record)

    db.commit()

    # Refresh to get auto-generated IDs
    for record in saved:
        db.refresh(record)

    return saved


def _check_cache(db: Session, scan_date: date, scan_type: str) -> list[ScanResult] | None:
    """
    Check if results already exist for this date+type.
    Returns cached results or None if no cache hit.
    """
    types_to_check = ["PPC", "NPC", "CONTRACTION"] if scan_type == "ALL" else [scan_type]

    cached: list[ScanResult] = []
    for stype in types_to_check:
        existing = (
            db.query(ScanResult)
            .filter(
                and_(
                    ScanResult.scan_date == scan_date,
                    ScanResult.scan_type == stype,
                )
            )
            .all()
        )
        cached.extend(existing)

    # Only return cache if we found results for ALL requested types
    if cached:
        return cached
    return None


@router.post("/run", response_model=list[ScanResultResponse])
async def run_scan(request: ScanRequest, db: Session = Depends(get_db)):
    """Trigger a scan and save results to the database."""
    scan_date = request.date or date.today()
    scan_type = request.scan_type.upper()

    if scan_type not in ("PPC", "NPC", "CONTRACTION", "ALL"):
        raise HTTPException(status_code=400, detail=f"Invalid scan_type: {scan_type}")

    logger.info(f"Starting {scan_type} scan for {scan_date}")

    try:
        scan_date_str = str(scan_date)

        if scan_type == "ALL":
            # Single download, all three scans
            results = await run_all_scans(scan_date_str)
        elif scan_type == "PPC":
            results = await run_ppc_scan(scan_date_str)
        elif scan_type == "NPC":
            results = await run_npc_scan(scan_date_str)
        else:
            results = await run_contraction_scan(scan_date_str)

        # Save to DB
        saved_records = _save_results(db, results)
        logger.info(f"Saved {len(saved_records)} scan results to database")

        return saved_records

    except Exception as exc:
        logger.error(f"Scan failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(exc)}")


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
