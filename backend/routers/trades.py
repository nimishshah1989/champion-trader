from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import PartialExit, Trade, get_db
from backend.models.trade import (
    PartialExitCreate,
    TradeClose,
    TradeCreate,
    TradeResponse,
    TradeStats,
    TradeUpdate,
)

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("", response_model=list[TradeResponse])
def get_trades(
    status: Optional[str] = Query(None, description="OPEN, PARTIAL, CLOSED, or ALL"),
    db: Session = Depends(get_db),
):
    """Get trades filtered by status."""
    query = db.query(Trade)
    if status and status != "ALL":
        query = query.filter(Trade.status == status.upper())
    return query.order_by(Trade.entry_date.desc()).all()


@router.post("", response_model=TradeResponse)
def create_trade(trade: TradeCreate, db: Session = Depends(get_db)):
    """Create a new trade record."""
    db_trade = Trade(
        symbol=trade.symbol.upper(),
        entry_date=trade.entry_date,
        entry_type=trade.entry_type,
        entry_price_half1=trade.entry_price_half1,
        entry_price_half2=trade.entry_price_half2,
        qty_half1=trade.qty_half1,
        qty_half2=trade.qty_half2,
        total_qty=trade.total_qty,
        avg_entry_price=trade.avg_entry_price,
        trp_at_entry=trade.trp_at_entry,
        sl_price=trade.sl_price,
        sl_pct=trade.sl_pct,
        rpt_amount=trade.rpt_amount,
        target_2r=trade.target_2r,
        target_ne=trade.target_ne,
        target_ge=trade.target_ge,
        target_ee=trade.target_ee,
        remaining_qty=trade.total_qty,
        market_stance_at_entry=trade.market_stance_at_entry,
        setup_type=trade.setup_type,
        entry_notes=trade.entry_notes,
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade


@router.get("/stats", response_model=TradeStats)
def get_trade_stats(db: Session = Depends(get_db)):
    """Aggregate trade statistics: win rate, ARR, total P&L."""
    all_trades = db.query(Trade).all()
    closed_trades = [t for t in all_trades if t.status == "CLOSED"]

    wins = [t for t in closed_trades if t.gross_pnl and t.gross_pnl > 0]
    losses = [t for t in closed_trades if t.gross_pnl and t.gross_pnl <= 0]

    win_rate = None
    if closed_trades:
        win_rate = round(len(wins) / len(closed_trades) * 100, 2)

    avg_win_r = None
    avg_loss_r = None
    if wins:
        win_rs = [t.r_multiple for t in wins if t.r_multiple is not None]
        if win_rs:
            avg_win_r = round(sum(win_rs) / len(win_rs), 2)
    if losses:
        loss_rs = [abs(t.r_multiple) for t in losses if t.r_multiple is not None]
        if loss_rs:
            avg_loss_r = round(sum(loss_rs) / len(loss_rs), 2)

    arr = None
    if avg_win_r and avg_loss_r and avg_loss_r > 0:
        arr = round(avg_win_r / avg_loss_r, 2)

    total_pnl = sum(t.gross_pnl for t in closed_trades if t.gross_pnl) or 0

    return TradeStats(
        total_trades=len(all_trades),
        open_trades=len([t for t in all_trades if t.status in ("OPEN", "PARTIAL")]),
        closed_trades=len(closed_trades),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=win_rate,
        avg_r_multiple=avg_win_r,
        arr=arr,
        total_pnl=round(total_pnl, 2),
    )


@router.get("/{trade_id}", response_model=TradeResponse)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Get full trade detail."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.patch("/{trade_id}/partial-exit")
def record_partial_exit(
    trade_id: int, exit_data: PartialExitCreate, db: Session = Depends(get_db)
):
    """Record a partial exit for a trade and recalculate remaining position."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if trade.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Trade is already closed")

    if trade.remaining_qty is not None and exit_data.exit_qty > trade.remaining_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Exit qty ({exit_data.exit_qty}) exceeds remaining qty ({trade.remaining_qty})",
        )

    # Calculate R-multiple for this partial exit
    r_multiple = None
    if trade.avg_entry_price and trade.trp_at_entry:
        trp_value = trade.avg_entry_price * (trade.trp_at_entry / 100)
        if trp_value > 0:
            r_multiple = round(
                (exit_data.exit_price - trade.avg_entry_price) / trp_value, 2
            )

    # Calculate P&L for this exit
    pnl = None
    if trade.avg_entry_price:
        pnl = round(
            (exit_data.exit_price - trade.avg_entry_price) * exit_data.exit_qty, 2
        )

    partial = PartialExit(
        trade_id=trade_id,
        exit_date=exit_data.exit_date,
        exit_price=exit_data.exit_price,
        exit_qty=exit_data.exit_qty,
        exit_reason=exit_data.exit_reason,
        r_multiple_at_exit=r_multiple,
        pnl=pnl,
        notes=exit_data.notes,
    )
    db.add(partial)

    # Update remaining qty
    if trade.remaining_qty is not None:
        trade.remaining_qty -= exit_data.exit_qty
        if trade.remaining_qty <= 0:
            trade.status = "CLOSED"
            trade.exit_date = exit_data.exit_date
            trade.exit_price = exit_data.exit_price
            trade.exit_method = exit_data.exit_reason
        else:
            trade.status = "PARTIAL"

    db.commit()
    return {"message": "Partial exit recorded", "remaining_qty": trade.remaining_qty}


@router.patch("/{trade_id}/close")
def close_trade(trade_id: int, close: TradeClose, db: Session = Depends(get_db)):
    """Fully close a trade."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if trade.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Trade is already closed")

    trade.exit_date = close.exit_date
    trade.exit_price = close.exit_price
    trade.exit_method = close.exit_reason
    trade.exit_notes = close.exit_notes
    trade.status = "CLOSED"

    # Calculate final P&L
    if trade.avg_entry_price and trade.total_qty:
        trade.gross_pnl = round(
            (close.exit_price - trade.avg_entry_price) * trade.total_qty, 2
        )
        trade.pnl_pct = round(
            ((close.exit_price - trade.avg_entry_price) / trade.avg_entry_price) * 100,
            2,
        )
        if trade.trp_at_entry:
            trp_value = trade.avg_entry_price * (trade.trp_at_entry / 100)
            if trp_value > 0:
                trade.r_multiple = round(
                    (close.exit_price - trade.avg_entry_price) / trp_value, 2
                )

    trade.remaining_qty = 0
    db.commit()
    return {"message": f"Trade {trade.symbol} closed", "gross_pnl": trade.gross_pnl}
