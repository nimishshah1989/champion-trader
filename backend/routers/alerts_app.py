from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import AppAlert, get_db

router = APIRouter(prefix="/alerts", tags=["In-App Alerts"])


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    symbol: Optional[str] = None
    title: str
    message: str
    severity: str
    is_read: bool
    created_at: Optional[str] = None
    data: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AlertResponse])
def get_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Fetch in-app alerts, newest first. Optionally filter to unread only."""
    query = db.query(AppAlert)
    if unread_only:
        query = query.filter(AppAlert.is_read == False)
    return query.order_by(desc(AppAlert.id)).limit(limit).all()


@router.get("/unread-count")
def get_unread_count(db: Session = Depends(get_db)):
    """Return the number of unread alerts (for badge display)."""
    count = db.query(AppAlert).filter(AppAlert.is_read == False).count()
    return {"count": count}


@router.patch("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db)):
    """Mark a single alert as read."""
    alert = db.query(AppAlert).filter(AppAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    return {"message": "Alert marked as read"}


@router.patch("/read-all")
def mark_all_read(db: Session = Depends(get_db)):
    """Mark every unread alert as read (bulk dismiss)."""
    db.query(AppAlert).filter(AppAlert.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "All alerts marked as read"}
