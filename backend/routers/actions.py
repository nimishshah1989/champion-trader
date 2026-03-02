from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import (
    ActionAlert,
    PartialExit,
    Trade,
    Watchlist,
    get_db,
)
from backend.models.action_alert import (
    ActionAlertResponse,
    ActOnAlertRequest,
    PriceCheckRequest,
    PriceCheckResponse,
)
from backend.services.price_monitor import run_price_check

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.post("/check-prices", response_model=PriceCheckResponse)
def check_prices(
    account_value: Optional[float] = Query(None),
    rpt_pct: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    """Run price check against watchlist and open trades. Returns all pending alerts."""
    result = run_price_check(db, account_value=account_value, rpt_pct=rpt_pct)

    buy_alerts = [ActionAlertResponse.model_validate(a) for a in result["buy_alerts"]]
    sell_alerts = [ActionAlertResponse.model_validate(a) for a in result["sell_alerts"]]

    return PriceCheckResponse(
        buy_alerts=buy_alerts,
        sell_alerts=sell_alerts,
        last_checked=result["last_checked"],
        prices_fetched=result["prices_fetched"],
    )


@router.get("", response_model=list[ActionAlertResponse])
def get_action_alerts(
    category: Optional[str] = Query(None, description="BUY or SELL"),
    status: Optional[str] = Query("NEW", description="NEW, ACTED, DISMISSED, EXPIRED"),
    db: Session = Depends(get_db),
):
    """List action alerts filtered by category and status."""
    query = db.query(ActionAlert)

    if category:
        query = query.filter(ActionAlert.alert_category == category.upper())
    if status:
        query = query.filter(ActionAlert.status == status.upper())

    alerts = query.order_by(ActionAlert.created_at.desc()).all()
    return alerts


@router.patch("/{alert_id}/act", response_model=ActionAlertResponse)
def act_on_alert(
    alert_id: int,
    body: Optional[ActOnAlertRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Mark alert as ACTED and auto-create the corresponding Trade (BUY) or PartialExit/Close (SELL).
    """
    alert = db.query(ActionAlert).filter(ActionAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != "NEW":
        raise HTTPException(status_code=400, detail=f"Alert already {alert.status}")

    actual_price = body.actual_price if body and body.actual_price else alert.current_price
    notes = body.notes if body else None

    if alert.alert_category == "BUY":
        # Create a trade from the BUY alert
        import json

        from backend.services.position_calculator import calculate_position

        entry_price = actual_price or alert.suggested_entry_price or 0
        trp_pct = alert.trp_pct or 3.0

        # Recalculate sizing and targets based on actual entry price
        account_value = alert.account_value_used or 500000.0
        rpt_pct = alert.rpt_pct_used or 0.5
        sizing = calculate_position(account_value, rpt_pct, entry_price, trp_pct)

        total_qty = sizing["position_size"]
        half_qty = sizing["half_qty"]
        sl_price = sizing["sl_price"]

        new_trade = Trade(
            symbol=alert.symbol,
            entry_date=date.today(),
            entry_type="LIVE_BREAK",
            entry_price_half1=entry_price,
            qty_half1=half_qty,
            total_qty=total_qty,
            avg_entry_price=entry_price,
            trp_at_entry=trp_pct,
            sl_price=sl_price,
            sl_pct=trp_pct,
            rpt_amount=sizing["rpt_amount"],
            target_2r=sizing["target_2r"],
            target_ne=sizing["target_ne"],
            target_ge=sizing["target_ge"],
            target_ee=sizing["target_ee"],
            remaining_qty=total_qty,
            entry_notes=notes or f"Auto-created from action alert #{alert.id}",
        )
        db.add(new_trade)
        db.flush()
        alert.resulting_trade_id = new_trade.id

        # Mark watchlist item as TRADED
        if alert.watchlist_id:
            wl = db.query(Watchlist).filter(Watchlist.id == alert.watchlist_id).first()
            if wl:
                wl.status = "TRADED"

    elif alert.alert_category == "SELL":
        trade = db.query(Trade).filter(Trade.id == alert.trade_id).first()
        if not trade:
            raise HTTPException(status_code=400, detail="Referenced trade not found")

        exit_price = actual_price or alert.current_price or 0
        exit_qty = alert.exit_qty or 0
        exit_reason = alert.alert_type.replace("_HIT", "").replace("FINAL_EXIT", "FINAL_50DMA")

        if alert.alert_type == "SL_HIT":
            # Full close
            trade.exit_date = date.today()
            trade.exit_price = exit_price
            trade.exit_method = "SL"
            trade.status = "CLOSED"
            if trade.avg_entry_price and trade.total_qty:
                trade.gross_pnl = round((exit_price - trade.avg_entry_price) * trade.total_qty, 2)
                trade.pnl_pct = round(((exit_price - trade.avg_entry_price) / trade.avg_entry_price) * 100, 2)
                if trade.trp_at_entry:
                    trp_value = trade.avg_entry_price * (trade.trp_at_entry / 100)
                    if trp_value > 0:
                        trade.r_multiple = round((exit_price - trade.avg_entry_price) / trp_value, 2)
            trade.remaining_qty = 0
            trade.exit_notes = notes or f"SL hit — auto-closed from alert #{alert.id}"
        else:
            # Partial exit
            r_multiple = None
            if trade.avg_entry_price and trade.trp_at_entry:
                trp_value = trade.avg_entry_price * (trade.trp_at_entry / 100)
                if trp_value > 0:
                    r_multiple = round((exit_price - trade.avg_entry_price) / trp_value, 2)

            pnl = round((exit_price - (trade.avg_entry_price or 0)) * exit_qty, 2)

            partial = PartialExit(
                trade_id=trade.id,
                exit_date=date.today(),
                exit_price=exit_price,
                exit_qty=exit_qty,
                exit_reason=exit_reason,
                r_multiple_at_exit=r_multiple,
                pnl=pnl,
                notes=notes or f"Auto-created from alert #{alert.id}",
            )
            db.add(partial)
            db.flush()
            alert.resulting_partial_exit_id = partial.id

            # Update remaining qty
            if trade.remaining_qty is not None:
                trade.remaining_qty -= exit_qty
                if trade.remaining_qty <= 0:
                    trade.status = "CLOSED"
                    trade.exit_date = date.today()
                    trade.exit_price = exit_price
                    trade.exit_method = exit_reason
                else:
                    trade.status = "PARTIAL"

    alert.status = "ACTED"
    alert.acted_at = datetime.now()

    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}/dismiss", response_model=ActionAlertResponse)
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark alert as DISMISSED."""
    alert = db.query(ActionAlert).filter(ActionAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != "NEW":
        raise HTTPException(status_code=400, detail=f"Alert already {alert.status}")

    alert.status = "DISMISSED"
    alert.acted_at = datetime.now()
    db.commit()
    db.refresh(alert)
    return alert
