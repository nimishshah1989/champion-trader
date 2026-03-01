import json
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import Column, Float, Integer, String, Text, desc, text
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import Base, ScanResult, get_db
from backend.services.alert_service import create_alert

logger = logging.getLogger("cts.webhooks")

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    received_at = Column(String, server_default=text("(datetime('now'))"))
    source = Column(String, nullable=False)  # tradingview, dhan
    alert_type = Column(String)
    symbol = Column(String)
    price = Column(Float)
    raw_payload = Column(Text)  # Full JSON for debugging
    status = Column(String, default="received")  # received, processed, error
    error_message = Column(Text)


# --- Request/Response models ---

class TradingViewAlert(BaseModel):
    """
    Flexible model for TradingView webhook alerts.
    TradingView sends whatever JSON you configure in the alert message.
    """
    symbol: str
    alert_type: str = Field(
        description="ENTRY | SL_HIT | PPC_DETECTED | NPC_DETECTED | CONTRACTION | CUSTOM"
    )
    price: float = 0
    close: Optional[float] = None
    volume: Optional[int] = None
    timeframe: Optional[str] = None
    exchange: Optional[str] = "NSE"
    timestamp: Optional[str] = None
    message: Optional[str] = None

    # PPC/NPC specific fields
    trp: Optional[float] = None
    trp_ratio: Optional[float] = None
    volume_ratio: Optional[float] = None
    close_position: Optional[float] = None  # 0-1, where close is in candle range

    # Entry specific fields
    trigger_level: Optional[float] = None

    # SL specific fields
    sl_price: Optional[float] = None


class WebhookLogResponse(BaseModel):
    id: int
    received_at: Optional[str] = None
    source: str
    alert_type: Optional[str] = None
    symbol: Optional[str] = None
    price: Optional[float] = None
    status: str

    model_config = {"from_attributes": True}


# --- Webhook endpoints ---

@router.post("/tradingview")
async def receive_tradingview_alert(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(None),
):
    """
    Receive alerts from TradingView Pine Script alerts.

    **TradingView Setup:**
    Set your alert's Webhook URL to:
    `https://your-domain.com/webhook/tradingview`

    Set the alert message body to JSON like:
    ```json
    {
      "symbol": "{{ticker}}",
      "alert_type": "PPC_DETECTED",
      "price": {{close}},
      "close": {{close}},
      "volume": {{volume}},
      "timeframe": "{{interval}}",
      "exchange": "{{exchange}}",
      "timestamp": "{{timenow}}",
      "message": "PPC detected on {{ticker}}"
    }
    ```

    **Security:** Set the `X-Webhook-Secret` header or include
    `"secret": "your_secret"` in the JSON body to authenticate.
    """
    # Parse raw body (TradingView sends JSON as text/plain sometimes)
    try:
        body = await request.body()
        raw_text = body.decode("utf-8")
        payload = json.loads(raw_text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        # Log the failed parse attempt
        log_entry = WebhookLog(
            source="tradingview",
            raw_payload=raw_text if "raw_text" in dir() else str(body),
            status="error",
            error_message=f"Failed to parse JSON: {exc}",
        )
        db.add(log_entry)
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Validate webhook secret (check header first, then body field)
    incoming_secret = x_webhook_secret or payload.get("secret")
    if settings.webhook_secret and settings.webhook_secret != "your_secret_key_here":
        if incoming_secret != settings.webhook_secret:
            log_entry = WebhookLog(
                source="tradingview",
                raw_payload=raw_text,
                status="error",
                error_message="Invalid webhook secret",
            )
            db.add(log_entry)
            db.commit()
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Parse into our model (with fallbacks for TradingView variable names)
    try:
        alert = TradingViewAlert(
            symbol=payload.get("symbol", payload.get("ticker", "UNKNOWN")),
            alert_type=payload.get("alert_type", payload.get("type", "CUSTOM")),
            price=float(payload.get("price", payload.get("close", 0))),
            close=_safe_float(payload.get("close")),
            volume=_safe_int(payload.get("volume")),
            timeframe=payload.get("timeframe", payload.get("interval")),
            exchange=payload.get("exchange", "NSE"),
            timestamp=payload.get("timestamp", payload.get("timenow")),
            message=payload.get("message"),
            trp=_safe_float(payload.get("trp")),
            trp_ratio=_safe_float(payload.get("trp_ratio")),
            volume_ratio=_safe_float(payload.get("volume_ratio")),
            close_position=_safe_float(payload.get("close_position")),
            trigger_level=_safe_float(payload.get("trigger_level")),
            sl_price=_safe_float(payload.get("sl_price")),
        )
    except Exception as exc:
        log_entry = WebhookLog(
            source="tradingview",
            raw_payload=raw_text,
            status="error",
            error_message=f"Failed to parse alert fields: {exc}",
        )
        db.add(log_entry)
        db.commit()
        raise HTTPException(status_code=422, detail=f"Invalid alert data: {exc}")

    # Log to webhook_logs table
    log_entry = WebhookLog(
        source="tradingview",
        alert_type=alert.alert_type,
        symbol=alert.symbol,
        price=alert.price,
        raw_payload=raw_text,
        status="received",
    )
    db.add(log_entry)

    # Clean symbol for display (remove exchange suffix)
    clean_symbol = alert.symbol.upper().replace(".NS", "")

    # Route based on alert type
    result = {"status": "received", "alert_type": alert.alert_type, "symbol": alert.symbol}

    if alert.alert_type in ("PPC_DETECTED", "NPC_DETECTED", "CONTRACTION"):
        scan_type_map = {
            "PPC_DETECTED": "PPC",
            "NPC_DETECTED": "NPC",
            "CONTRACTION": "CONTRACTION",
        }
        scan_result = ScanResult(
            scan_date=date.today(),
            symbol=clean_symbol,
            scan_type=scan_type_map[alert.alert_type],
            close_price=alert.close or alert.price,
            volume=alert.volume,
            volume_ratio=alert.volume_ratio,
            trp=alert.trp,
            trp_ratio=alert.trp_ratio,
            close_position=alert.close_position,
            trigger_level=alert.trigger_level,
            notes=alert.message,
        )
        db.add(scan_result)
        log_entry.status = "processed"
        result["action"] = f"Saved to scan_results as {scan_type_map[alert.alert_type]}"

        # Create in-app alert for scan detections
        scan_label = scan_type_map[alert.alert_type]
        trp_info = f" TRP ratio: {alert.trp_ratio}x," if alert.trp_ratio else ""
        vol_info = f" Volume ratio: {alert.volume_ratio}x" if alert.volume_ratio else ""
        create_alert(
            db,
            alert.alert_type,
            f"{clean_symbol} {scan_label} detected at {alert.price}.{trp_info}{vol_info}",
            symbol=clean_symbol,
            data={
                "price": alert.price,
                "trp_ratio": alert.trp_ratio,
                "volume_ratio": alert.volume_ratio,
            },
        )

    elif alert.alert_type == "ENTRY":
        log_entry.status = "processed"
        result["action"] = "Entry alert logged"
        result["trigger_level"] = alert.trigger_level
        result["message"] = f"{alert.symbol} broke trigger level at {alert.price}"

        # Create in-app alert for entry trigger
        create_alert(
            db,
            "TRIGGER_LEVEL",
            f"{clean_symbol} broke trigger level at {alert.price}",
            symbol=clean_symbol,
            data={
                "price": alert.price,
                "trigger_level": alert.trigger_level,
            },
        )

    elif alert.alert_type == "SL_HIT":
        log_entry.status = "processed"
        result["action"] = "SL hit alert logged — monitor for 10 minutes before exiting"
        result["sl_price"] = alert.sl_price or alert.price

        # Create critical in-app alert for SL hit
        create_alert(
            db,
            "SL_HIT",
            f"{clean_symbol} hit stop-loss at {alert.sl_price or alert.price}. Monitor for 10 minutes before exiting.",
            symbol=clean_symbol,
            data={
                "price": alert.price,
                "sl_price": alert.sl_price or alert.price,
            },
        )

    else:
        log_entry.status = "processed"
        result["action"] = "Custom alert logged"

        # Create in-app alert for custom/unknown types
        custom_message = alert.message or f"Custom alert for {clean_symbol} at {alert.price}"
        create_alert(
            db,
            alert.alert_type,
            custom_message,
            symbol=clean_symbol,
            data={"price": alert.price, "raw_type": alert.alert_type},
        )

    db.commit()

    logger.info(
        "TradingView alert: type=%s symbol=%s price=%s",
        alert.alert_type, alert.symbol, alert.price,
    )

    return result


@router.get("/tradingview/logs", response_model=list[WebhookLogResponse])
def get_webhook_logs(
    limit: int = Query(default=50, ge=1, le=500),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get recent webhook logs for debugging."""
    query = db.query(WebhookLog)
    if source:
        query = query.filter(WebhookLog.source == source)
    return query.order_by(desc(WebhookLog.id)).limit(limit).all()


@router.post("/dhan")
async def receive_dhan_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive order execution confirmations from Dhan.
    Logs the raw payload for now — full processing in Phase 6.
    """
    try:
        body = await request.body()
        raw_text = body.decode("utf-8")
        payload = json.loads(raw_text)
    except Exception:
        payload = {}
        raw_text = str(await request.body())

    log_entry = WebhookLog(
        source="dhan",
        symbol=payload.get("symbol"),
        raw_payload=raw_text,
        status="received",
    )
    db.add(log_entry)
    db.commit()

    return {"status": "received", "message": "Dhan webhook logged — full processing in Phase 6"}


@router.get("/test")
def webhook_test():
    """Simple endpoint to verify webhook URL is reachable."""
    return {
        "status": "ok",
        "message": "Webhook endpoint is active",
        "tradingview_url": "/webhook/tradingview",
        "dhan_url": "/webhook/dhan",
    }


# --- Helpers ---

def _safe_float(value) -> Optional[float]:
    """Safely convert a value to float, handling TradingView template vars."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> Optional[int]:
    """Safely convert a value to int."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
