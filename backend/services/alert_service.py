import json
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import AppAlert

# Maps alert_type to default severity and title template.
# {symbol} is replaced at runtime; for types without a symbol the raw template is used.
ALERT_CONFIG = {
    "SL_HIT": {"severity": "critical", "title_template": "SL Alert: {symbol}"},
    "TRIGGER_LEVEL": {"severity": "warning", "title_template": "Entry Alert: {symbol}"},
    "PPC_DETECTED": {"severity": "info", "title_template": "PPC Detected: {symbol}"},
    "NPC_DETECTED": {"severity": "info", "title_template": "NPC Detected: {symbol}"},
    "CONTRACTION": {"severity": "info", "title_template": "Contraction: {symbol}"},
    "2R_HIT": {"severity": "info", "title_template": "2R Target Hit: {symbol}"},
    "EXTENSION": {"severity": "info", "title_template": "Extension: {symbol}"},
    "EARNINGS_WARNING": {"severity": "warning", "title_template": "Earnings Warning: {symbol}"},
    "MARKET_STANCE": {"severity": "info", "title_template": "Market Stance Update"},
    "SYSTEM": {"severity": "info", "title_template": "System Alert"},
}


def create_alert(
    db: Session,
    alert_type: str,
    message: str,
    symbol: Optional[str] = None,
    title: Optional[str] = None,
    data: Optional[dict] = None,
) -> AppAlert:
    """
    Create and persist a new in-app alert.

    If title is not provided, it is generated from ALERT_CONFIG using the
    alert_type and symbol.
    """
    config = ALERT_CONFIG.get(alert_type, {"severity": "info", "title_template": "Alert"})

    if title is None:
        title = config["title_template"].format(symbol=symbol or "")

    alert = AppAlert(
        alert_type=alert_type,
        symbol=symbol,
        title=title,
        message=message,
        severity=config["severity"],
        data=json.dumps(data) if data else None,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
