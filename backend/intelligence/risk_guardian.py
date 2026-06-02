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
from decimal import Decimal

from backend.config import settings
from backend.database import SessionLocal, Trade
from backend.engine.runtime.config import RISK_V2, RiskParams
from backend.engine.runtime.risk_manager import update_halt
from backend.intelligence.risk_guardian_checks import (
    MAX_OPEN_RISK_PCT,
    PORTFOLIO_CHECK_INTERVAL_SECONDS,
    send_alert,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state — the v2 drawdown breaker (15% halt / 7.5% resume).
# ---------------------------------------------------------------------------
_frozen = False  # True when the drawdown breaker has tripped -- no new entries allowed

# Re-export the constant so any callers that imported it from here still work
PORTFOLIO_CHECK_INTERVAL_SECONDS = PORTFOLIO_CHECK_INTERVAL_SECONDS  # noqa: F811


def current_dd_halt(db, *, risk: RiskParams = RISK_V2,
                    start_capital: Decimal | None = None) -> tuple[bool, float, float]:
    """Replay the 15%/7.5% drawdown breaker over the realised equity curve.

    Returns (halted, equity, peak). Realised P&L only (closed trades, in exit order) — a
    conservative, network-free guard for the paper engine. Phase-2 LIVE marks open positions
    to market for a true intraday equity; the breaker thresholds live in RiskParams.
    """
    if start_capital is None:
        start_capital = Decimal(str(settings.paper_capital))
    closed = (db.query(Trade).filter(Trade.status == "CLOSED")
              .order_by(Trade.exit_date.asc(), Trade.id.asc()).all())
    equity = float(start_capital)
    peak = equity
    halted = False
    for t in closed:
        if t.gross_pnl is not None:
            equity += float(t.gross_pnl)
        peak = max(peak, equity)
        halted = update_halt(halted, equity, peak, risk)
    return halted, equity, peak


async def monitor_positions() -> None:
    """v2 portfolio guard — surface the drawdown breaker state + flag excess open risk.

    Per-position stop management is the post-close exit job's job now (exit_runtime's
    close-based chandelier). This guard tracks the 15%-halt / 7.5%-resume breaker and
    publishes it via `is_frozen()` (for /health + the FREEZE Telegram alert). The entry pass
    does not rely on this flag — it recomputes the same halt directly at fill time through
    `current_dd_halt`, so a freeze is enforced even outside the guard's market-hours cadence.
    """
    global _frozen

    db = SessionLocal()
    try:
        halted, equity, peak = current_dd_halt(db)
        was, _frozen = _frozen, halted
        if halted and not was:
            logger.warning(f"HALT: drawdown breaker tripped — equity ₹{equity:,.0f} vs "
                           f"peak ₹{peak:,.0f}; new entries FROZEN")
            await send_alert(f"Drawdown breaker tripped: equity ₹{equity:,.0f} vs "
                             f"peak ₹{peak:,.0f}. New entries FROZEN.")
        elif was and not halted:
            logger.info(f"RESUME: drawdown recovered — equity ₹{equity:,.0f}; entries unfrozen")

        open_trades = db.query(Trade).filter(Trade.status.in_(["OPEN", "PARTIAL"])).all()
        open_risk = sum((Decimal(str(t.rpt_amount or 0)) for t in open_trades), Decimal("0"))
        cap = Decimal(str(equity)) * Decimal(str(MAX_OPEN_RISK_PCT)) / Decimal("100")
        if open_risk > cap:
            logger.warning(f"OPEN RISK ₹{open_risk:,.0f} exceeds {MAX_OPEN_RISK_PCT}% "
                           f"cap ₹{cap:,.0f} across {len(open_trades)} positions")
    except Exception as e:
        logger.error(f"Risk guardian error: {e}")
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
