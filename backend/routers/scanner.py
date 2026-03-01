from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import ScanResult, get_db
from backend.models.scan_result import ScanRequest, ScanResultResponse
from backend.services.scanner_engine import (
    run_contraction_scan,
    run_npc_scan,
    run_ppc_scan,
)

router = APIRouter(prefix="/scanner", tags=["Scanner"])


@router.post("/run", response_model=list[ScanResultResponse])
async def run_scan(request: ScanRequest, db: Session = Depends(get_db)):
    """Trigger a scan and save results to the database."""
    scan_date = request.date or date.today()
    results = []

    if request.scan_type in ("PPC", "ALL"):
        results.extend(await run_ppc_scan(str(scan_date)))
    if request.scan_type in ("NPC", "ALL"):
        results.extend(await run_npc_scan(str(scan_date)))
    if request.scan_type in ("CONTRACTION", "ALL"):
        results.extend(await run_contraction_scan(str(scan_date)))

    # TODO: Save results to DB once scanner engine is implemented
    return results


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
        query = query.filter(ScanResult.scan_type == scan_type)
    return query.order_by(desc(ScanResult.scan_date)).all()


@router.get("/results/latest", response_model=list[ScanResultResponse])
def get_latest_results(db: Session = Depends(get_db)):
    """Get the most recent scan results grouped by type."""
    # Find the latest scan date
    latest = db.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
    if not latest:
        return []
    return (
        db.query(ScanResult)
        .filter(ScanResult.scan_date == latest[0])
        .all()
    )
