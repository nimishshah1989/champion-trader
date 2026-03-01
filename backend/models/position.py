from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PositionCalcRequest(BaseModel):
    symbol: str
    account_value: float = Field(gt=0)
    rpt_pct: float = Field(gt=0, le=1.0)  # 0.2% to 1.0%
    entry_price: float = Field(gt=0)
    trp_pct: float = Field(gt=0)  # e.g. 3.18 for 3.18%


class PositionCalcResponse(BaseModel):
    rpt_amount: float
    sl_price: float
    sl_pct: float
    sl_amount: float
    position_value: float
    position_size: int  # shares
    half_qty: int
    target_2r: float
    target_ne: float  # Normal Extension = 4x TRP
    target_ge: float  # Great Extension = 8x TRP
    target_ee: float  # Extreme Extension = 12x TRP


class PyramidCalcRequest(BaseModel):
    trade_id: int
    current_price: float = Field(gt=0)
    current_qty: int = Field(gt=0)
    available_capital: float = Field(gt=0)


class PyramidCalcResponse(BaseModel):
    recommended_add_qty: int
    add_position_value: float
    new_avg_price: float
    new_total_qty: int
    new_sl_price: float
    notes: str


class PositionCalcSessionResponse(BaseModel):
    id: int
    calc_date: date
    symbol: str
    account_value: float
    rpt_pct: float
    rpt_amount: float
    entry_price: float
    sl_pct: float
    sl_amount: float
    sl_price: float
    position_value: float
    position_size: int
    half_qty: int
    target_2r: Optional[float] = None
    target_ne: Optional[float] = None
    target_ge: Optional[float] = None
    target_ee: Optional[float] = None

    model_config = {"from_attributes": True}
