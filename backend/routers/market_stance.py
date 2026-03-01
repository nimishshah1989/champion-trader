from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import MarketStanceLog, get_db

from pydantic import BaseModel


class StanceLogCreate(BaseModel):
    log_date: date
    strong_sectors: list[str] = []
    weak_sectors: list[str] = []
    stance: str  # WEAK, MODERATE, STRONG
    rpt_pct: Optional[float] = None
    max_positions: Optional[int] = None
    notes: Optional[str] = None


class StanceLogResponse(BaseModel):
    id: int
    log_date: date
    strong_sectors: Optional[str] = None
    weak_sectors: Optional[str] = None
    strong_count: Optional[int] = None
    weak_count: Optional[int] = None
    stance: Optional[str] = None
    rpt_pct: Optional[float] = None
    max_positions: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/market-stance", tags=["Market Stance"])


@router.post("/log", response_model=StanceLogResponse)
def log_stance(entry: StanceLogCreate, db: Session = Depends(get_db)):
    """Log daily market stance assessment."""
    # Check for existing entry on same date
    existing = (
        db.query(MarketStanceLog)
        .filter(MarketStanceLog.log_date == entry.log_date)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Stance already logged for {entry.log_date}",
        )

    db_entry = MarketStanceLog(
        log_date=entry.log_date,
        strong_sectors=",".join(entry.strong_sectors),
        weak_sectors=",".join(entry.weak_sectors),
        strong_count=len(entry.strong_sectors),
        weak_count=len(entry.weak_sectors),
        stance=entry.stance.upper(),
        rpt_pct=entry.rpt_pct,
        max_positions=entry.max_positions,
        notes=entry.notes,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


@router.get("/latest", response_model=Optional[StanceLogResponse])
def get_latest_stance(db: Session = Depends(get_db)):
    """Get today's or the most recent market stance."""
    stance = (
        db.query(MarketStanceLog)
        .order_by(desc(MarketStanceLog.log_date))
        .first()
    )
    if not stance:
        return None
    return stance


@router.get("/history", response_model=list[StanceLogResponse])
def get_stance_history(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get stance history for the last N days."""
    cutoff = date.today() - timedelta(days=days)
    return (
        db.query(MarketStanceLog)
        .filter(MarketStanceLog.log_date >= cutoff)
        .order_by(desc(MarketStanceLog.log_date))
        .all()
    )
