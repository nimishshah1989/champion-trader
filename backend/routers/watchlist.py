from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import Watchlist, get_db
from backend.models.watchlist import (
    AlertResponse,
    WatchlistAdd,
    WatchlistResponse,
    WatchlistUpdate,
)

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("", response_model=list[WatchlistResponse])
def get_watchlist(db: Session = Depends(get_db)):
    """Get all active watchlist entries grouped by bucket."""
    return (
        db.query(Watchlist)
        .filter(Watchlist.status == "ACTIVE")
        .order_by(Watchlist.bucket, Watchlist.symbol)
        .all()
    )


@router.post("/add", response_model=WatchlistResponse)
def add_to_watchlist(item: WatchlistAdd, db: Session = Depends(get_db)):
    """Add a stock to the watchlist."""
    db_item = Watchlist(
        symbol=item.symbol.upper(),
        added_date=date.today(),
        bucket=item.bucket.upper(),
        stage=item.stage,
        base_days=item.base_days,
        base_quality=item.base_quality,
        trigger_level=item.trigger_level,
        planned_entry_price=item.planned_entry_price,
        planned_sl_pct=item.planned_sl_pct,
        wuc_types=item.wuc_types,
        notes=item.notes,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/{item_id}", response_model=WatchlistResponse)
def update_watchlist_item(
    item_id: int, update: WatchlistUpdate, db: Session = Depends(get_db)
):
    """Update a watchlist item's bucket, parameters, or status."""
    db_item = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}")
def remove_from_watchlist(item_id: int, db: Session = Depends(get_db)):
    """Remove a stock from watchlist (sets status to REMOVED)."""
    db_item = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    db_item.status = "REMOVED"
    db.commit()
    return {"message": f"{db_item.symbol} removed from watchlist"}


@router.get("/alerts", response_model=list[AlertResponse])
def get_alerts(db: Session = Depends(get_db)):
    """Get all READY stocks with trigger levels for alert setting."""
    ready_stocks = (
        db.query(Watchlist)
        .filter(Watchlist.status == "ACTIVE", Watchlist.bucket == "READY")
        .filter(Watchlist.trigger_level.isnot(None))
        .all()
    )
    return [
        AlertResponse(
            symbol=s.symbol,
            trigger_level=s.trigger_level,
            planned_sl_pct=s.planned_sl_pct,
            notes=s.notes,
        )
        for s in ready_stocks
    ]
