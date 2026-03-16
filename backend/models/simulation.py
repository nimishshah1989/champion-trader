from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    start_date: date
    end_date: date
    starting_capital: Decimal = Field(default=Decimal("100000"), description="Starting capital in INR")
    rpt_pct: float = Field(default=0.5, ge=0.2, le=1.0, description="Risk per trade %")
    name: Optional[str] = None


class PaperStartRequest(BaseModel):
    starting_capital: Decimal = Field(default=Decimal("100000"), description="Starting capital in INR")
    rpt_pct: float = Field(default=0.5, ge=0.2, le=1.0, description="Risk per trade %")
    name: Optional[str] = None


class SimulationTradeResponse(BaseModel):
    id: int
    run_id: int
    symbol: str
    signal_date: Optional[date] = None
    entry_date: Optional[date] = None
    entry_price: Optional[Decimal] = None
    total_qty: Optional[int] = None
    half_qty: Optional[int] = None
    trp_pct: Optional[float] = None
    sl_price: Optional[Decimal] = None
    rpt_amount: Optional[Decimal] = None
    target_2r: Optional[Decimal] = None
    target_ne: Optional[Decimal] = None
    target_ge: Optional[Decimal] = None
    target_ee: Optional[Decimal] = None

    qty_exited_2r: int = 0
    qty_exited_ne: int = 0
    qty_exited_ge: int = 0
    qty_exited_ee: int = 0
    qty_exited_sl: int = 0
    qty_exited_final: int = 0
    remaining_qty: Optional[int] = None

    status: str = "OPEN"
    exit_date: Optional[date] = None
    gross_pnl: Optional[Decimal] = None
    r_multiple: Optional[float] = None
    pnl_pct: Optional[float] = None
    portfolio_value_at_entry: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class EquityCurvePoint(BaseModel):
    date: str
    equity: Decimal


class SimulationRunResponse(BaseModel):
    id: int
    run_type: str
    name: Optional[str] = None
    starting_capital: Decimal
    rpt_pct: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str

    # Summary results
    final_capital: Optional[Decimal] = None
    total_pnl: Optional[Decimal] = None
    total_return_pct: Optional[float] = None
    total_trades: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate: Optional[float] = None
    avg_win_r: Optional[float] = None
    avg_loss_r: Optional[float] = None
    arr: Optional[float] = None
    expectancy: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    max_drawdown_amount: Optional[Decimal] = None

    equity_curve: Optional[str] = None  # JSON string
    last_processed_date: Optional[date] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class SimulationRunWithTrades(SimulationRunResponse):
    trades: list[SimulationTradeResponse] = []
