from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


class TradingViewAlert(BaseModel):
    symbol: str
    alert_type: str  # ENTRY, SL_HIT, PPC_DETECTED, NPC_DETECTED
    price: float
    timestamp: Optional[str] = None
    message: Optional[str] = None


class DhanWebhook(BaseModel):
    """Placeholder for Dhan order execution confirmations."""
    order_id: Optional[str] = None
    status: Optional[str] = None
    symbol: Optional[str] = None
    qty: Optional[int] = None
    price: Optional[float] = None


@router.post("/tradingview")
async def receive_tradingview_alert(alert: TradingViewAlert):
    """
    Receive alerts from TradingView Pine Script alerts.

    Routes to appropriate action based on alert_type:
    - ENTRY: Notify via Telegram, update watchlist to READY
    - SL_HIT: Send immediate Telegram alert to monitor for 10 mins
    - PPC_DETECTED: Add to scan results
    - NPC_DETECTED: Flag sector as weak

    TODO: Implement routing logic in Phase 5.
    """
    # TODO: Validate webhook secret
    # TODO: Route to appropriate handler based on alert_type
    # TODO: Send Telegram notification
    return {
        "status": "received",
        "alert_type": alert.alert_type,
        "symbol": alert.symbol,
        "message": "Webhook processing not yet implemented — Phase 5",
    }


@router.post("/dhan")
async def receive_dhan_webhook(payload: DhanWebhook):
    """
    Receive order execution confirmations from Dhan.
    TODO: Implement in Phase 6.
    """
    return {
        "status": "received",
        "message": "Dhan webhook processing not yet implemented — Phase 6",
    }
