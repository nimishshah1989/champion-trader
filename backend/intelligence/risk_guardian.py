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

Individual check functions are in risk_guardian_checks.py.
"""

from __future__ import annotations

import logging
from datetime import datetime

from backend.database import SessionLocal, Trade
from backend.intelligence.risk_guardian_checks import (
    PORTFOLIO_CHECK_INTERVAL_SECONDS,
    batch_fetch_prices,
    check_single_position,
    portfolio_level_checks,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_frozen = False  # True if month drawdown > 6% -- no new entries allowed
_last_portfolio_check: datetime | None = None

# Re-export the constant so any callers that imported it from here still work
PORTFOLIO_CHECK_INTERVAL_SECONDS = PORTFOLIO_CHECK_INTERVAL_SECONDS  # noqa: F811


async def monitor_positions() -> None:
    """
    Main monitoring loop -- called every 10 minutes by APScheduler.
    Fetches live prices, checks SL breaches, updates trailing stops,
    and runs portfolio-level risk checks on a 30-minute cadence.
    """
    global _last_portfolio_check, _frozen

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
        prices = await batch_fetch_prices(symbols)

        for trade in open_trades:
            live_price = prices.get(trade.symbol)
            if live_price is None or live_price <= 0:
                logger.warning(f"No price for {trade.symbol}, skipping")
                continue

            await check_single_position(db, trade, live_price)

        db.commit()

        now = datetime.now()
        should_run_portfolio = (
            _last_portfolio_check is None
            or (now - _last_portfolio_check).seconds >= PORTFOLIO_CHECK_INTERVAL_SECONDS
        )
        if should_run_portfolio:
            _frozen = await portfolio_level_checks(db, open_trades, prices, _frozen)
            _last_portfolio_check = now

    except Exception as e:
        logger.error(f"Position monitoring error: {e}")
        db.rollback()
    finally:
        db.close()


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
