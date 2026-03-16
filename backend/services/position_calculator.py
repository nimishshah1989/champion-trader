"""
Position Calculator — fully implemented.

This is the core position sizing logic from the Champion Trader methodology.
Calculates how many shares to buy based on account value, risk per trade,
entry price, and the stock's True Range Percentage (TRP).

Formula:
    RPT Amount = Account Value x (RPT% / 100)
    SL Price = Entry Price - (Entry Price x TRP% / 100)
    Position Value = RPT Amount / (TRP% / 100)
    Position Size = round(Position Value / Entry Price)
    Half Qty = Position Size // 2

Extension targets (from entry price):
    2R  = Entry + 2 x TRP value
    NE  = Entry + 4 x TRP value (Normal Extension)
    GE  = Entry + 8 x TRP value (Great Extension)
    EE  = Entry + 12 x TRP value (Extreme Extension)
"""

from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def calculate_position(
    account_value: Decimal,
    rpt_pct: float,
    entry_price: Decimal,
    trp_pct: float,
) -> dict:
    """
    Calculate position size and all derived values.

    Args:
        account_value: Total trading capital (e.g. Decimal("500000"))
        rpt_pct: Risk per trade as percentage (e.g. 0.50 for 0.5%)
        entry_price: Planned entry price (e.g. Decimal("601"))
        trp_pct: True Range Percentage (e.g. 3.18 for 3.18%)

    Returns:
        Dict with all position sizing values and extension targets.
        Financial values are Decimal; sl_pct remains float.

    Test cases from source document:
        ASTERDM:   AV=500000, RPT=0.50%, Entry=601,  TRP=3.18% -> Size=131, Half=65
        MARICO:    AV=500000, RPT=0.50%, Entry=724.5, TRP=1.85% -> Size=188, Half=94
        SWARAJENG: AV=500000, RPT=0.50%, Entry=4482,  TRP=3.30% -> Size=17,  Half=8
    """
    # Ensure inputs are Decimal
    if not isinstance(account_value, Decimal):
        account_value = Decimal(str(account_value))
    if not isinstance(entry_price, Decimal):
        entry_price = Decimal(str(entry_price))

    rpt_amount = account_value * Decimal(str(rpt_pct)) / Decimal("100")

    sl_pct_decimal = Decimal(str(trp_pct)) / Decimal("100")
    sl_amount = entry_price * sl_pct_decimal
    sl_price = entry_price - sl_amount

    position_value = rpt_amount / sl_pct_decimal
    position_size = int((position_value / entry_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    half_qty = position_size // 2

    # TRP value in rupees = same as initial SL amount
    trp_value = sl_amount

    return {
        "rpt_amount": rpt_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        "sl_price": sl_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        "sl_pct": round(trp_pct, 2),
        "sl_amount": sl_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        "position_value": position_value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        "position_size": position_size,
        "half_qty": half_qty,
        "target_2r": (entry_price + Decimal("2") * trp_value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        "target_ne": (entry_price + Decimal("4") * trp_value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        "target_ge": (entry_price + Decimal("8") * trp_value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        "target_ee": (entry_price + Decimal("12") * trp_value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
    }
