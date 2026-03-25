"""
Backtest metric calculation functions.

Extracted from backtest_engine.py to keep file sizes under 400 lines.
"""

from __future__ import annotations

from backend.database import SimulationTrade


def compute_total_pnl(pos: SimulationTrade, entry_price: float, sl_exit_price: float | None = None) -> float:
    """Compute total P&L from all partial and SL exits (excluding final exit).

    sl_exit_price: the actual SL price used for exit (may be trailed up from original).
    If not provided, falls back to pos.sl_price (original SL).
    """
    total = 0.0
    if pos.qty_exited_2r and pos.target_2r:
        total += (pos.target_2r - entry_price) * pos.qty_exited_2r
    if pos.qty_exited_ne and pos.target_ne:
        total += (pos.target_ne - entry_price) * pos.qty_exited_ne
    if pos.qty_exited_ge and pos.target_ge:
        total += (pos.target_ge - entry_price) * pos.qty_exited_ge
    if pos.qty_exited_ee and pos.target_ee:
        total += (pos.target_ee - entry_price) * pos.qty_exited_ee
    if pos.qty_exited_sl:
        actual_sl = sl_exit_price if sl_exit_price is not None else (pos.sl_price or 0)
        total += (actual_sl - entry_price) * pos.qty_exited_sl
    return total
