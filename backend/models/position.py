from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PositionCalcRequest(BaseModel):
    symbol: str
    account_value: Decimal = Field(gt=0)
    rpt_pct: float = Field(gt=0, le=1.0)  # 0.2% to 1.0%
    entry_price: Decimal = Field(gt=0)
    trp_pct: float = Field(gt=0)  # e.g. 3.18 for 3.18%


class PositionCalcResponse(BaseModel):
    rpt_amount: Decimal
    sl_price: Decimal
    sl_pct: float
    sl_amount: Decimal
    position_value: Decimal
    position_size: int  # shares
    half_qty: int
    target_2r: Decimal
    target_ne: Decimal  # Normal Extension = 4x TRP
    target_ge: Decimal  # Great Extension = 8x TRP
    target_ee: Decimal  # Extreme Extension = 12x TRP


class PyramidCalcRequest(BaseModel):
    trade_id: int
    current_price: Decimal = Field(gt=0)
    current_qty: int = Field(gt=0)
    available_capital: Decimal = Field(gt=0)


class PyramidCalcResponse(BaseModel):
    recommended_add_qty: int
    add_position_value: Decimal
    new_avg_price: Decimal
    new_total_qty: int
    new_sl_price: Decimal
    notes: str


class PositionCalcSessionResponse(BaseModel):
    id: int
    calc_date: date
    symbol: str
    account_value: Decimal
    rpt_pct: float
    rpt_amount: Decimal
    entry_price: Decimal
    sl_pct: float
    sl_amount: Decimal
    sl_price: Decimal
    position_value: Decimal
    position_size: int
    half_qty: int
    target_2r: Optional[Decimal] = None
    target_ne: Optional[Decimal] = None
    target_ge: Optional[Decimal] = None
    target_ee: Optional[Decimal] = None

    model_config = {"from_attributes": True}
