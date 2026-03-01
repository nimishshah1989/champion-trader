from datetime import date
from typing import Optional

from pydantic import BaseModel


class ScanRequest(BaseModel):
    scan_type: str  # PPC, NPC, CONTRACTION, ALL
    date: Optional[date] = None  # defaults to today


class ScanResultResponse(BaseModel):
    id: int
    scan_date: date
    symbol: str
    scan_type: str
    close_price: Optional[float] = None
    volume: Optional[int] = None
    avg_volume_20d: Optional[float] = None
    volume_ratio: Optional[float] = None
    trp: Optional[float] = None
    avg_trp: Optional[float] = None
    trp_ratio: Optional[float] = None
    candle_body_pct: Optional[float] = None
    close_position: Optional[float] = None
    stage: Optional[str] = None
    above_30w_ma: Optional[bool] = None
    ma_trending_up: Optional[bool] = None
    base_days: Optional[int] = None
    has_min_20_bar_base: Optional[bool] = None
    base_quality: Optional[str] = None
    adt: Optional[float] = None
    passes_liquidity_filter: Optional[bool] = None
    wuc_type: Optional[str] = None
    watchlist_bucket: Optional[str] = None
    trigger_level: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}
