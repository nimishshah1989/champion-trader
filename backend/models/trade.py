from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class TradeCreate(BaseModel):
    symbol: str
    entry_date: date
    entry_type: Optional[str] = None  # LIVE_BREAK, CLOSE_ABOVE, NEXT_DAY_HIGH
    entry_price_half1: float
    entry_price_half2: Optional[float] = None
    qty_half1: int
    qty_half2: Optional[int] = None
    total_qty: int
    avg_entry_price: float
    trp_at_entry: float
    sl_price: float
    sl_pct: float
    rpt_amount: float
    target_2r: Optional[float] = None
    target_ne: Optional[float] = None
    target_ge: Optional[float] = None
    target_ee: Optional[float] = None
    market_stance_at_entry: Optional[str] = None
    setup_type: Optional[str] = None
    entry_notes: Optional[str] = None


class TradeUpdate(BaseModel):
    entry_price_half2: Optional[float] = None
    qty_half2: Optional[int] = None
    total_qty: Optional[int] = None
    avg_entry_price: Optional[float] = None
    sl_price: Optional[float] = None
    entry_notes: Optional[str] = None
    exit_notes: Optional[str] = None


class PartialExitCreate(BaseModel):
    exit_date: date
    exit_price: float
    exit_qty: int
    exit_reason: str  # 2R, NE, GE, EE, EARNINGS_RISK, MANUAL
    notes: Optional[str] = None


class TradeClose(BaseModel):
    exit_price: float
    exit_reason: str
    exit_date: date
    exit_notes: Optional[str] = None


class TradeResponse(BaseModel):
    id: int
    symbol: str
    entry_date: date
    entry_type: Optional[str] = None
    avg_entry_price: Optional[float] = None
    total_qty: Optional[int] = None
    sl_price: Optional[float] = None
    sl_pct: Optional[float] = None
    rpt_amount: Optional[float] = None
    target_2r: Optional[float] = None
    target_ne: Optional[float] = None
    target_ge: Optional[float] = None
    target_ee: Optional[float] = None
    status: str
    remaining_qty: Optional[int] = None
    gross_pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    pnl_pct: Optional[float] = None
    setup_type: Optional[str] = None

    model_config = {"from_attributes": True}


class TradeStats(BaseModel):
    total_trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate: Optional[float] = None
    avg_r_multiple: Optional[float] = None
    arr: Optional[float] = None  # Average Reward:Risk ratio
    total_pnl: float = 0
