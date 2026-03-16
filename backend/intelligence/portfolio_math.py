"""
portfolio_math.py — Portfolio-level risk mathematics.

Functions:
  - calculate_var: Value at Risk (historical simulation)
  - calculate_correlation_matrix: Sector concentration risk
  - calculate_drawdown: Peak-to-trough drawdown from equity curve
  - calculate_monthly_pnl: Month-to-date P&L from trades
  - calculate_open_risk: Total open risk across all positions
  - calculate_sector_concentration: Positions per sector
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def calculate_var(
    position_values: list[float],
    daily_returns: list[list[float]],
    confidence: float = 0.95,
) -> float:
    """
    Calculate Value at Risk using historical simulation.

    Args:
        position_values: current value of each position
        daily_returns: list of daily return series per position
        confidence: VaR confidence level (default 95%)

    Returns:
        VaR amount (positive number representing potential loss)
    """
    if not position_values or not daily_returns:
        return 0.0

    # Calculate portfolio returns
    weights = np.array(position_values)
    total = weights.sum()
    if total == 0:
        return 0.0
    weights = weights / total

    # Build portfolio return series
    min_len = min(len(r) for r in daily_returns)
    if min_len < 5:
        return 0.0

    portfolio_returns = np.zeros(min_len)
    for i, returns in enumerate(daily_returns):
        portfolio_returns += weights[i] * np.array(returns[:min_len])

    # VaR = quantile of losses
    var_pct = np.percentile(portfolio_returns, (1 - confidence) * 100)
    var_amount = abs(var_pct) * total

    return round(var_amount, 2)


def calculate_correlation_matrix(
    return_series: dict[str, list[float]],
) -> dict[str, dict[str, float]]:
    """
    Calculate pairwise correlation between position returns.

    Args:
        return_series: {symbol: [daily_returns]}

    Returns:
        Nested dict of correlations: {sym1: {sym2: corr}}
    """
    if len(return_series) < 2:
        return {}

    symbols = list(return_series.keys())
    min_len = min(len(v) for v in return_series.values())

    if min_len < 10:
        return {}

    matrix = {}
    for i, sym_i in enumerate(symbols):
        matrix[sym_i] = {}
        for j, sym_j in enumerate(symbols):
            returns_i = np.array(return_series[sym_i][:min_len])
            returns_j = np.array(return_series[sym_j][:min_len])
            corr = np.corrcoef(returns_i, returns_j)[0, 1]
            matrix[sym_i][sym_j] = round(float(corr), 4)

    return matrix


def calculate_drawdown(equity_curve: list[float]) -> dict:
    """
    Calculate drawdown metrics from an equity curve.

    Returns:
        {
            "max_drawdown_pct": float,
            "max_drawdown_amount": float,
            "current_drawdown_pct": float,
            "peak": float,
            "trough": float,
        }
    """
    if not equity_curve or len(equity_curve) < 2:
        return {
            "max_drawdown_pct": 0.0,
            "max_drawdown_amount": 0.0,
            "current_drawdown_pct": 0.0,
            "peak": 0.0,
            "trough": 0.0,
        }

    values = np.array(equity_curve)
    peak = np.maximum.accumulate(values)
    drawdown = (values - peak) / peak

    max_dd_idx = np.argmin(drawdown)
    max_dd_pct = abs(float(drawdown[max_dd_idx]))

    peak_val = float(peak[max_dd_idx])
    trough_val = float(values[max_dd_idx])

    current_dd = abs(float(drawdown[-1]))

    return {
        "max_drawdown_pct": round(max_dd_pct, 4),
        "max_drawdown_amount": round(peak_val - trough_val, 2),
        "current_drawdown_pct": round(current_dd, 4),
        "peak": round(peak_val, 2),
        "trough": round(trough_val, 2),
    }


def calculate_monthly_pnl(trades: list[dict]) -> dict:
    """
    Calculate month-to-date P&L from trade records.

    Args:
        trades: list of trade dicts with 'exit_date', 'total_pnl', 'status'

    Returns:
        {
            "mtd_pnl": float,
            "mtd_trades": int,
            "mtd_wins": int,
            "mtd_losses": int,
            "mtd_win_rate": float,
        }
    """
    now = datetime.now()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")

    mtd_trades = []
    for t in trades:
        exit_date = t.get("exit_date")
        if exit_date and str(exit_date) >= month_start and t.get("status") in ("CLOSED", "STOPPED"):
            mtd_trades.append(t)

    total_pnl = sum(t.get("total_pnl", 0) or 0 for t in mtd_trades)
    wins = sum(1 for t in mtd_trades if (t.get("total_pnl", 0) or 0) > 0)
    losses = len(mtd_trades) - wins
    win_rate = wins / len(mtd_trades) if mtd_trades else 0

    return {
        "mtd_pnl": round(total_pnl, 2),
        "mtd_trades": len(mtd_trades),
        "mtd_wins": wins,
        "mtd_losses": losses,
        "mtd_win_rate": round(win_rate, 4),
    }


def calculate_open_risk(
    positions: list[dict],
    account_value: float,
) -> dict:
    """
    Calculate total open risk across all positions.

    Args:
        positions: list of dicts with 'remaining_qty', 'avg_entry_price', 'stop_loss'
        account_value: current account value

    Returns:
        {
            "total_risk_amount": float,
            "total_risk_pct": float,
            "exceeds_limit": bool,  (True if > 10% of AV)
            "per_position": [{symbol, risk_amount, risk_pct}]
        }
    """
    # Ensure account_value is float (may be Decimal from config)
    account_value = float(account_value)

    per_position = []
    total_risk = 0.0

    for pos in positions:
        qty = pos.get("remaining_qty", 0) or 0
        entry = float(pos.get("avg_entry_price", 0) or 0)
        sl = float(pos.get("stop_loss", 0) or 0)
        symbol = pos.get("symbol", "UNKNOWN")

        if qty > 0 and entry > 0 and sl > 0:
            risk_per_share = entry - sl
            risk_amount = qty * risk_per_share
            risk_pct = (risk_amount / account_value) * 100 if account_value > 0 else 0

            per_position.append({
                "symbol": symbol,
                "risk_amount": round(risk_amount, 2),
                "risk_pct": round(risk_pct, 2),
            })
            total_risk += risk_amount

    total_risk_pct = (total_risk / account_value) * 100 if account_value > 0 else 0

    return {
        "total_risk_amount": round(total_risk, 2),
        "total_risk_pct": round(total_risk_pct, 2),
        "exceeds_limit": total_risk_pct > 10.0,
        "per_position": per_position,
    }


def calculate_sector_concentration(positions: list[dict]) -> dict:
    """
    Check sector concentration — flag if 2+ positions in same sector.

    Args:
        positions: list of dicts with 'symbol', 'sector'

    Returns:
        {
            "concentrated_sectors": [{"sector": str, "count": int, "symbols": [str]}],
            "has_concentration_risk": bool,
        }
    """
    sector_map: dict[str, list[str]] = {}
    for pos in positions:
        sector = pos.get("sector", "Unknown")
        symbol = pos.get("symbol", "")
        if sector not in sector_map:
            sector_map[sector] = []
        sector_map[sector].append(symbol)

    concentrated = [
        {"sector": sector, "count": len(symbols), "symbols": symbols}
        for sector, symbols in sector_map.items()
        if len(symbols) >= 2
    ]

    return {
        "concentrated_sectors": concentrated,
        "has_concentration_risk": len(concentrated) > 0,
    }
