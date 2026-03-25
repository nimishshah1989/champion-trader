"""
risk_guardian_checks.py -- Individual position and portfolio-level check functions.

Single-position checks:
  - SL breach detection and execution
  - Trailing stop logic (breakeven, 2R, LOD)

Portfolio-level checks:
  - Total open risk > 10% warning
  - Month drawdown > 6% freeze
  - Sector concentration flagging

Price fetching and Telegram alerting utilities.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

import yfinance as yf

from backend.config import settings
from backend.database import Stock, Trade
from backend.intelligence.broker_client import get_broker_client
from backend.intelligence.portfolio_math import (
    calculate_monthly_pnl,
    calculate_open_risk,
    calculate_sector_concentration,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------
PORTFOLIO_CHECK_INTERVAL_SECONDS = 1800  # 30 minutes
MAX_OPEN_RISK_PCT = 10.0
MONTH_DRAWDOWN_FREEZE_PCT = 0.06  # 6% of account value
TRAIL_BREAKEVEN_THRESHOLD_R = 2.0
TRAIL_2R_THRESHOLD_R = 4.0
TRAIL_LOD_THRESHOLD_R = 8.0
LOD_LOOKBACK_DAYS = 5
LOD_PRIOR_DAY_INDEX = -2


# ---------------------------------------------------------------------------
# Single-position check
# ---------------------------------------------------------------------------

async def check_single_position(db: object, trade: Trade, live_price: float) -> None:
    """Check a single position for SL breach and trailing stop updates."""
    effective_sl = Decimal(str(trade.sl_price or 0))
    entry_price = Decimal(str(trade.avg_entry_price or 0))

    # TRP value in absolute rupees: entry_price * (trp_at_entry / 100)
    trp_pct = Decimal(str(trade.trp_at_entry or 0))
    trp_value = entry_price * (trp_pct / Decimal("100")) if trp_pct else Decimal("0")

    if not trp_value or not entry_price or not effective_sl:
        return

    # Unrealised R-multiple
    unrealised_move = live_price - entry_price
    r_multiple = unrealised_move / trp_value if trp_value > 0 else 0

    # 1. SL BREACH
    if live_price <= effective_sl:
        logger.warning(
            f"SL BREACH: {trade.symbol} @ {live_price:.2f} "
            f"<= SL {effective_sl:.2f}"
        )
        await execute_sl_exit(db, trade, live_price)
        return

    # 2. TRAILING STOP LOGIC (SL only moves UP, never down)
    new_sl = effective_sl

    if r_multiple >= TRAIL_LOD_THRESHOLD_R:
        # Trail using prior day low (LOD method)
        lod_sl = fetch_prior_day_low(trade.symbol)
        if lod_sl is not None and lod_sl > new_sl:
            new_sl = round(lod_sl, 2)
            logger.info(
                f"{trade.symbol}: LOD trail to {new_sl:.2f} "
                f"(R={r_multiple:.1f})"
            )
    elif r_multiple >= TRAIL_2R_THRESHOLD_R:
        sl_at_2r = entry_price + (2 * trp_value)
        if sl_at_2r > new_sl:
            new_sl = round(sl_at_2r, 2)
            logger.info(
                f"{trade.symbol}: Trail to 2R {new_sl:.2f} "
                f"(R={r_multiple:.1f})"
            )
    elif r_multiple >= TRAIL_BREAKEVEN_THRESHOLD_R:
        if entry_price > new_sl:
            new_sl = round(entry_price, 2)
            logger.info(
                f"{trade.symbol}: Trail to breakeven {new_sl:.2f} "
                f"(R={r_multiple:.1f})"
            )

    # Persist only upward moves
    if new_sl > effective_sl:
        trade.sl_price = new_sl
        logger.info(
            f"{trade.symbol}: SL updated {effective_sl:.2f} -> {new_sl:.2f}"
        )


def fetch_prior_day_low(symbol: str) -> float | None:
    """Fetch the prior trading day's low for LOD trailing."""
    try:
        data = yf.download(
            f"{symbol}.NS",
            period=f"{LOD_LOOKBACK_DAYS}d",
            progress=False,
        )
        if isinstance(data.columns, __import__("pandas").MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if len(data) >= 2:
            return float(data["Low"].iloc[LOD_PRIOR_DAY_INDEX])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# SL exit execution
# ---------------------------------------------------------------------------

async def execute_sl_exit(db: object, trade: Trade, exit_price: float) -> None:
    """Execute stop loss exit -- the ONLY autonomous action."""
    broker = get_broker_client()

    remaining = trade.remaining_qty or 0
    if remaining <= 0:
        return

    entry_price = float(trade.avg_entry_price or 0)
    trp_pct = float(trade.trp_at_entry or 0)
    trp_value = entry_price * (trp_pct / 100) if trp_pct else 1

    try:
        await broker.place_market_order(
            symbol=trade.symbol,
            qty=remaining,
            order_type="SELL",
        )

        # Update trade record
        trade.status = "CLOSED"
        trade.exit_price = exit_price
        trade.exit_date = datetime.now().date()
        trade.exit_method = "SL_HIT"
        trade.exit_qty = remaining
        trade.remaining_qty = 0

        # P&L
        pnl = (exit_price - entry_price) * remaining
        trade.gross_pnl = (trade.gross_pnl or 0) + pnl
        trade.r_multiple = (
            round((exit_price - entry_price) / trp_value, 2)
            if trp_value > 0
            else 0
        )
        trade.pnl_pct = (
            round(((exit_price - entry_price) / entry_price) * 100, 2)
            if entry_price > 0
            else 0
        )

        logger.warning(
            f"SL EXECUTED: {trade.symbol} sold {remaining} @ "
            f"{exit_price:.2f} | P&L: {pnl:,.0f} | R: {trade.r_multiple}"
        )

        await send_alert(
            f"STOP LOSS: {trade.symbol} sold {remaining} "
            f"@ {exit_price:.2f}\n"
            f"P&L: {pnl:,.0f} | R: {trade.r_multiple}"
        )

    except Exception as e:
        logger.error(f"SL execution failed for {trade.symbol}: {e}")


# ---------------------------------------------------------------------------
# Portfolio-level checks
# ---------------------------------------------------------------------------

async def portfolio_level_checks(
    db: object,
    trades: list[Trade],
    prices: dict[str, float],
    frozen: bool,
) -> bool:
    """
    Run portfolio-level risk checks every 30 minutes.
    Returns the updated frozen state.
    """
    account_value = settings.default_account_value  # Already Decimal from config

    # Build a sector lookup from the stocks table
    symbols = [t.symbol for t in trades]
    sector_map = build_sector_map(db, symbols)

    # Build position list for risk calc.
    positions = []
    for t in trades:
        positions.append(
            {
                "symbol": t.symbol,
                "remaining_qty": t.remaining_qty,
                "avg_entry_price": t.avg_entry_price,
                "stop_loss": t.sl_price,  # mapped for portfolio_math API
                "sector": sector_map.get(t.symbol, "Unknown"),
            }
        )

    # --- Open risk ---
    risk = calculate_open_risk(positions, account_value)
    if risk["exceeds_limit"]:
        logger.warning(
            f"RISK LIMIT: Open risk at {risk['total_risk_pct']:.1f}% "
            f"(limit: {MAX_OPEN_RISK_PCT}%)"
        )
        await send_alert(
            f"Open risk at {risk['total_risk_pct']:.1f}% of account "
            f"-- exceeds {MAX_OPEN_RISK_PCT}% limit!"
        )

    # --- Sector concentration ---
    concentration = calculate_sector_concentration(positions)
    if concentration["has_concentration_risk"]:
        sectors = concentration["concentrated_sectors"]
        logger.warning(f"Sector concentration: {sectors}")

    # --- Month drawdown ---
    closed_this_month = (
        db.query(Trade)
        .filter(Trade.status.in_(["CLOSED", "STOPPED"]))
        .all()
    )
    mtd = calculate_monthly_pnl(
        [
            {
                "total_pnl": t.gross_pnl,
                "exit_date": str(t.exit_date) if t.exit_date else None,
                "status": t.status,
            }
            for t in closed_this_month
        ]
    )

    freeze_threshold = account_value * MONTH_DRAWDOWN_FREEZE_PCT
    if mtd["mtd_pnl"] < -freeze_threshold:
        if not frozen:
            frozen = True
            logger.warning(
                "FREEZE: Month drawdown exceeds 6% -- new entries blocked"
            )
            await send_alert(
                f"Month drawdown exceeds 6% ({mtd['mtd_pnl']:,.0f}). "
                f"New entries FROZEN."
            )

    return frozen


def build_sector_map(db: object, symbols: list[str]) -> dict[str, str]:
    """Look up sectors for a list of symbols from the stocks table."""
    sector_map: dict[str, str] = {}
    if not symbols:
        return sector_map
    try:
        stocks = (
            db.query(Stock.symbol, Stock.sector)
            .filter(Stock.symbol.in_(symbols))
            .all()
        )
        for s in stocks:
            sector_map[s.symbol] = s.sector or "Unknown"
    except Exception as e:
        logger.error(f"Sector lookup failed: {e}")
    return sector_map


# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------

async def batch_fetch_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch live prices for multiple NSE symbols via yfinance."""
    prices: dict[str, float] = {}
    if not symbols:
        return prices

    try:
        tickers = [f"{s}.NS" for s in symbols]
        data = yf.download(tickers, period="1d", progress=False)

        pd = __import__("pandas")
        if isinstance(data.columns, pd.MultiIndex):
            for sym in symbols:
                ticker = f"{sym}.NS"
                try:
                    if ticker in data.columns.get_level_values(1):
                        close = data["Close"][ticker].iloc[-1]
                        prices[sym] = float(close)
                except Exception:
                    continue
        elif len(symbols) == 1:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            prices[symbols[0]] = float(data["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"Batch price fetch failed: {e}")

    # Fallback: individual fetches for any missing symbols
    missing = [s for s in symbols if s not in prices]
    for sym in missing:
        try:
            ticker = yf.Ticker(f"{sym}.NS")
            p = ticker.info.get("regularMarketPrice") or ticker.info.get(
                "previousClose", 0
            )
            prices[sym] = float(p)
        except Exception:
            continue

    return prices


# ---------------------------------------------------------------------------
# Telegram helper
# ---------------------------------------------------------------------------

async def send_alert(message: str) -> None:
    """Send a Telegram alert, swallowing errors to avoid breaking the loop."""
    try:
        from backend.services.notifications import send_telegram_alert

        await send_telegram_alert(message)
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
