from datetime import date
from typing import Optional

from pydantic import BaseModel


class WatchlistAdd(BaseModel):
    symbol: str
    bucket: str  # READY, NEAR, AWAY
    stage: Optional[str] = None
    base_days: Optional[int] = None
    base_quality: Optional[str] = None
    trigger_level: Optional[float] = None
    planned_entry_price: Optional[float] = None
    planned_sl_pct: Optional[float] = None  # TRP%
    wuc_types: Optional[str] = None  # comma-separated
    notes: Optional[str] = None


class WatchlistUpdate(BaseModel):
    bucket: Optional[str] = None
    trigger_level: Optional[float] = None
    planned_entry_price: Optional[float] = None
    planned_sl_pct: Optional[float] = None
    planned_position_size: Optional[int] = None
    planned_half_qty: Optional[int] = None
    status: Optional[str] = None
    removed_reason: Optional[str] = None
    notes: Optional[str] = None


class WatchlistResponse(BaseModel):
    id: int
    symbol: str
    added_date: date
    bucket: str
    stage: Optional[str] = None
    base_days: Optional[int] = None
    base_quality: Optional[str] = None
    wuc_types: Optional[str] = None
    trigger_level: Optional[float] = None
    planned_entry_price: Optional[float] = None
    planned_sl_pct: Optional[float] = None
    planned_position_size: Optional[int] = None
    planned_half_qty: Optional[int] = None
    status: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    """READY stocks with trigger levels for alert setting."""

    symbol: str
    trigger_level: float
    planned_sl_pct: Optional[float] = None
    notes: Optional[str] = None
