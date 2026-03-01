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


def calculate_position(
    account_value: float,
    rpt_pct: float,
    entry_price: float,
    trp_pct: float,
) -> dict:
    """
    Calculate position size and all derived values.

    Args:
        account_value: Total trading capital (e.g. 500000)
        rpt_pct: Risk per trade as percentage (e.g. 0.50 for 0.5%)
        entry_price: Planned entry price (e.g. 601)
        trp_pct: True Range Percentage (e.g. 3.18 for 3.18%)

    Returns:
        Dict with all position sizing values and extension targets.

    Test cases from source document:
        ASTERDM:   AV=500000, RPT=0.50%, Entry=601,  TRP=3.18% -> Size=131, Half=65
        MARICO:    AV=500000, RPT=0.50%, Entry=724.5, TRP=1.85% -> Size=188, Half=94
        SWARAJENG: AV=500000, RPT=0.50%, Entry=4482,  TRP=3.30% -> Size=17,  Half=8
    """
    rpt_amount = account_value * (rpt_pct / 100)

    sl_pct_decimal = trp_pct / 100
    sl_amount = entry_price * sl_pct_decimal
    sl_price = entry_price - sl_amount

    position_value = rpt_amount / sl_pct_decimal
    position_size = round(position_value / entry_price)
    half_qty = position_size // 2

    # TRP value in rupees = same as initial SL amount
    trp_value = sl_amount

    return {
        "rpt_amount": round(rpt_amount, 2),
        "sl_price": round(sl_price, 2),
        "sl_pct": round(trp_pct, 2),
        "sl_amount": round(sl_amount, 2),
        "position_value": round(position_value, 2),
        "position_size": position_size,
        "half_qty": half_qty,
        "target_2r": round(entry_price + (2 * trp_value), 2),
        "target_ne": round(entry_price + (4 * trp_value), 2),
        "target_ge": round(entry_price + (8 * trp_value), 2),
        "target_ee": round(entry_price + (12 * trp_value), 2),
    }
