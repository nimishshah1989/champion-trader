"""
risk_guardian.py -- Live position monitor and stop loss executor.

Runs every 10 minutes from 09:15 to 15:30 IST on market days.

For each open position:
  1. Fetch live price
  2. Check: live_price <= effective_sl -> execute sell + Telegram alert
  3. Check trailing stop milestones:
     -> unrealised > 2R: trail to breakeven
     -> unrealised > 4R: trail to 2R level
     -> unrealised > 8R: trail using prior day low (LOD)
  4. Update sl_price in trades table

Portfolio-level checks (every 30 minutes):
  - Total open risk > 10% -> Telegram warning
  - Month drawdown > 6% -> FREEZE new entries
  - 2+ positions same sector -> flag

AUTONOMOUS: May ONLY place SELL orders for SL breach. Never BUY.
"""

from __future__ import annotations

import logging
from datetime import datetime

import yfinance as yf

from backend.config import settings
from backend.database import SessionLocal, Trade, Stock
from backend.intelligence.broker_client import get_broker_client
from backend.intelligence.portfolio_math import (
    calculate_monthly_pnl,
    calculate_open_risk,
    calculate_sector_concentration,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_frozen = False  # True if month drawdown > 6% -- no new entries allowed
_last_portfolio_check: datetime | None = None

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


async def monitor_positions() -> None:
    """
    Main monitoring loop -- called every 10 minutes by APScheduler.
    Fetches live prices, checks SL breaches, updates trailing stops,
    and runs portfolio-level risk checks on a 30-minute cadence.
    """
    global _last_portfolio_check

    db = SessionLocal()
    try:
        open_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
            .all()
        )

        if not open_trades:
            return

        logger.info(f"Monitoring {len(open_trades)} open positions")

        symbols = [t.symbol for t in open_trades]
        prices = await _batch_fetch_prices(symbols)

        for trade in open_trades:
            live_price = prices.get(trade.symbol)
            if live_price is None or live_price <= 0:
                logger.warning(f"No price for {trade.symbol}, skipping")
                continue

            await _check_single_position(db, trade, live_price)

        db.commit()

        now = datetime.now()
        should_run_portfolio = (
            _last_portfolio_check is None
            or (now - _last_portfolio_check).seconds >= PORTFOLIO_CHECK_INTERVAL_SECONDS
        )
        if should_run_portfolio:
            await _portfolio_level_checks(db, open_trades, prices)
            _last_portfolio_check = now

    except Exception as e:
        logger.error(f"Position monitoring error: {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Single-position check
# ---------------------------------------------------------------------------

async def _check_single_position(db, trade: Trade, live_price: float) -> None:
    """Check a single position for SL breach and trailing stop updates."""
    effective_sl = float(trade.sl_price or 0)
    entry_price = float(trade.avg_entry_price or 0)

    # TRP value in absolute rupees: entry_price * (trp_at_entry / 100)
    trp_pct = float(trade.trp_at_entry or 0)
    trp_value = entry_price * (trp_pct / 100) if trp_pct else 0

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
        await _execute_sl_exit(db, trade, live_price)
        return

    # 2. TRAILING STOP LOGIC (SL only moves UP, never down)
    new_sl = effective_sl

    if r_multiple >= TRAIL_LOD_THRESHOLD_R:
        # Trail using prior day low (LOD method)
        lod_sl = _fetch_prior_day_low(trade.symbol)
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


def _fetch_prior_day_low(symbol: str) -> float | None:
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

async def _execute_sl_exit(db, trade: Trade, exit_price: float) -> None:
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

        await _send_alert(
            f"STOP LOSS: {trade.symbol} sold {remaining} "
            f"@ {exit_price:.2f}\n"
            f"P&L: {pnl:,.0f} | R: {trade.r_multiple}"
        )

    except Exception as e:
        logger.error(f"SL execution failed for {trade.symbol}: {e}")


# ---------------------------------------------------------------------------
# Portfolio-level checks
# ---------------------------------------------------------------------------

async def _portfolio_level_checks(
    db, trades: list[Trade], prices: dict[str, float]
) -> None:
    """Run portfolio-level risk checks every 30 minutes."""
    global _frozen

    account_value = float(settings.default_account_value)  # Decimal → float for arithmetic

    # Build a sector lookup from the stocks table
    symbols = [t.symbol for t in trades]
    sector_map = _build_sector_map(db, symbols)

    # Build position list for risk calc.
    # calculate_open_risk expects key "stop_loss" (not sl_price).
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
        await _send_alert(
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
    # calculate_monthly_pnl expects dicts with "total_pnl" key, "exit_date",
    # and "status".  Map gross_pnl -> total_pnl for the helper.
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
        if not _frozen:
            _frozen = True
            logger.warning(
                "FREEZE: Month drawdown exceeds 6% -- new entries blocked"
            )
            await _send_alert(
                f"Month drawdown exceeds 6% ({mtd['mtd_pnl']:,.0f}). "
                f"New entries FROZEN."
            )


def _build_sector_map(db, symbols: list[str]) -> dict[str, str]:
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

async def _batch_fetch_prices(symbols: list[str]) -> dict[str, float]:
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

async def _send_alert(message: str) -> None:
    """Send a Telegram alert, swallowing errors to avoid breaking the loop."""
    try:
        from backend.services.notifications import send_telegram_alert

        await send_telegram_alert(message)
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_frozen() -> bool:
    """Check if new entries are frozen due to drawdown."""
    return _frozen


def unfreeze() -> None:
    """Manually unfreeze new entries (admin action)."""
    global _frozen
    _frozen = False
    logger.info("Entry freeze lifted manually")
