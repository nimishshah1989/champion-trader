from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TradeCreate(BaseModel):
    symbol: str
    entry_date: date
    entry_type: Optional[str] = None  # LIVE_BREAK, CLOSE_ABOVE, NEXT_DAY_HIGH
    entry_price_half1: Decimal
    entry_price_half2: Optional[Decimal] = None
    qty_half1: int
    qty_half2: Optional[int] = None
    total_qty: int
    avg_entry_price: Decimal
    trp_at_entry: Decimal
    sl_price: Decimal
    sl_pct: float
    rpt_amount: Decimal
    target_2r: Optional[Decimal] = None
    target_ne: Optional[Decimal] = None
    target_ge: Optional[Decimal] = None
    target_ee: Optional[Decimal] = None
    market_stance_at_entry: Optional[str] = None
    setup_type: Optional[str] = None
    entry_notes: Optional[str] = None


class TradeUpdate(BaseModel):
    entry_price_half2: Optional[Decimal] = None
    qty_half2: Optional[int] = None
    total_qty: Optional[int] = None
    avg_entry_price: Optional[Decimal] = None
    sl_price: Optional[Decimal] = None
    entry_notes: Optional[str] = None
    exit_notes: Optional[str] = None


class PartialExitCreate(BaseModel):
    exit_date: date
    exit_price: Decimal
    exit_qty: int
    exit_reason: str  # 2R, NE, GE, EE, EARNINGS_RISK, MANUAL
    notes: Optional[str] = None


class TradeClose(BaseModel):
    exit_price: Decimal
    exit_reason: str
    exit_date: date
    exit_notes: Optional[str] = None


class TradeResponse(BaseModel):
    id: int
    symbol: str
    entry_date: date
    entry_type: Optional[str] = None
    avg_entry_price: Optional[Decimal] = None
    total_qty: Optional[int] = None
    sl_price: Optional[Decimal] = None
    sl_pct: Optional[float] = None
    rpt_amount: Optional[Decimal] = None
    target_2r: Optional[Decimal] = None
    target_ne: Optional[Decimal] = None
    target_ge: Optional[Decimal] = None
    target_ee: Optional[Decimal] = None
    status: str
    remaining_qty: Optional[int] = None
    gross_pnl: Optional[Decimal] = None
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
    total_pnl: Decimal = Decimal("0")
