"""
autopilot_report.py -- Virtual portfolio reporting and status.

Separated from autopilot.py to stay under 400-line limit.
"""

from __future__ import annotations

from decimal import Decimal

from backend.database import SessionLocal, Trade
from backend.services.autopilot import VIRTUAL_CAPITAL, MAX_OPEN_RISK_PCT


def get_virtual_portfolio_summary() -> dict:
    """Return current state of the virtual portfolio."""
    db = SessionLocal()
    try:
        open_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
            .all()
        )
        closed_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["CLOSED", "STOPPED"]))
            .all()
        )

        open_risk = sum(float(t.rpt_amount or 0) for t in open_trades)
        total_pnl = sum(float(t.gross_pnl or 0) for t in closed_trades)
        wins = sum(1 for t in closed_trades if (t.gross_pnl or 0) > 0)
        losses = len(closed_trades) - wins
        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0

        return {
            "virtual_capital": float(VIRTUAL_CAPITAL),
            "open_positions": len(open_trades),
            "open_trades": [
                {
                    "symbol": t.symbol,
                    "entry_price": float(t.avg_entry_price or 0),
                    "qty": t.remaining_qty,
                    "sl_price": float(t.sl_price or 0),
                    "risk": float(t.rpt_amount or 0),
                }
                for t in open_trades
            ],
            "open_risk": open_risk,
            "max_risk": float(VIRTUAL_CAPITAL * MAX_OPEN_RISK_PCT / Decimal("100")),
            "closed_trades": len(closed_trades),
            "total_pnl": total_pnl,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "capital_after_pnl": float(VIRTUAL_CAPITAL) + total_pnl,
        }
    finally:
        db.close()
