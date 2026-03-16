from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import PositionCalcSession, get_db
from backend.models.position import (
    PositionCalcRequest,
    PositionCalcResponse,
    PyramidCalcRequest,
    PyramidCalcResponse,
)
from backend.services.position_calculator import calculate_position

router = APIRouter(prefix="/calculator", tags=["Calculator"])


@router.post("/position", response_model=PositionCalcResponse)
def calc_position(request: PositionCalcRequest, db: Session = Depends(get_db)):
    """
    Calculate position size, stop loss, and extension targets.

    This uses the exact formula from the Champion Trader methodology:
    - RPT Amount = Account Value x (RPT% / 100)
    - Position Value = RPT Amount / (TRP% / 100)
    - Position Size = int(Position Value / Entry Price)
    """
    result = calculate_position(
        account_value=request.account_value,
        rpt_pct=request.rpt_pct,
        entry_price=request.entry_price,
        trp_pct=request.trp_pct,
    )

    # Save the calculation session
    session = PositionCalcSession(
        calc_date=date.today(),
        symbol=request.symbol.upper(),
        account_value=request.account_value,
        rpt_pct=request.rpt_pct,
        rpt_amount=result["rpt_amount"],
        entry_price=request.entry_price,
        sl_pct=result["sl_pct"],
        sl_amount=result["sl_amount"],
        sl_price=result["sl_price"],
        position_value=result["position_value"],
        position_size=result["position_size"],
        half_qty=result["half_qty"],
        target_2r=result["target_2r"],
        target_ne=result["target_ne"],
        target_ge=result["target_ge"],
        target_ee=result["target_ee"],
    )
    db.add(session)
    db.commit()

    return PositionCalcResponse(**result)


@router.post("/pyramid", response_model=PyramidCalcResponse)
def calc_pyramid(request: PyramidCalcRequest):
    """
    Calculate pyramid add sizing for an existing winning trade.
    TODO: Full implementation in Phase 2.
    """
    # Stub: basic pyramid calculation
    # In a real pyramid, you add to a winning position with reduced risk
    TWO_PLACES = Decimal("0.01")
    add_qty = max(1, request.current_qty // 4)  # Add ~25% of current position
    add_value = add_qty * request.current_price

    return PyramidCalcResponse(
        recommended_add_qty=add_qty,
        add_position_value=add_value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        new_avg_price=request.current_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        new_total_qty=request.current_qty + add_qty,
        new_sl_price=Decimal("0"),  # TODO: calculate proper trailing SL
        notes="Pyramid calculation is a stub — full implementation in Phase 2",
    )
