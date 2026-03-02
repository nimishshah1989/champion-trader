from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PriceCheckRequest(BaseModel):
    account_value: Optional[float] = Field(None, description="Override account value (default from latest market stance)")
    rpt_pct: Optional[float] = Field(None, description="Override RPT% (default from latest market stance)")


class ActOnAlertRequest(BaseModel):
    actual_price: Optional[float] = Field(None, description="Override actual execution price")
    notes: Optional[str] = None


class ActionAlertResponse(BaseModel):
    id: int
    alert_category: str  # BUY, SELL
    alert_type: str  # TRIGGER_BREAK, SL_HIT, 2R_HIT, NE_HIT, GE_HIT, EE_HIT, FINAL_EXIT
    symbol: str
    current_price: Optional[float] = None
    trigger_price: Optional[float] = None

    # BUY fields
    suggested_qty: Optional[int] = None
    suggested_half_qty: Optional[int] = None
    suggested_sl_price: Optional[float] = None
    suggested_entry_price: Optional[float] = None
    account_value_used: Optional[float] = None
    rpt_pct_used: Optional[float] = None
    trp_pct: Optional[float] = None

    # SELL fields
    trade_id: Optional[int] = None
    exit_qty: Optional[int] = None
    exit_pct: Optional[float] = None
    target_level: Optional[float] = None
    remaining_qty_after: Optional[int] = None

    action_text: Optional[str] = None
    status: str = "NEW"
    acted_at: Optional[datetime] = None

    resulting_trade_id: Optional[int] = None
    resulting_partial_exit_id: Optional[int] = None

    source: Optional[str] = None
    watchlist_id: Optional[int] = None
    data: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class PriceCheckResponse(BaseModel):
    buy_alerts: list[ActionAlertResponse] = []
    sell_alerts: list[ActionAlertResponse] = []
    last_checked: str
    prices_fetched: int
