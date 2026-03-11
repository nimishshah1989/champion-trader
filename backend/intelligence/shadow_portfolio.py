"""
shadow_portfolio.py -- Parallel paper-trade simulator.

Every setup card from signal_agent is automatically paper-traded.
Tracks whether the human approved it for the live account.
After 30+ shadow trades, compares shadow vs live performance
to measure human alpha (or lack thereof).
"""

import logging
from datetime import date as date_type

import yfinance as yf

from backend.database import SessionLocal, ShadowTrade, Trade
from backend.intelligence.regime_classifier import get_latest_regime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------
MIN_SHADOW_TRADES_FOR_COMPARISON = 30
DEFAULT_R_ON_STOP = -1.0
DEFAULT_R_ON_TARGET = 2.0


# ---------------------------------------------------------------------------
# Record a setup card
# ---------------------------------------------------------------------------

async def track_setup(
    setup_card: dict, was_approved: bool = False
) -> None:
    """
    Record a setup card as a shadow trade.
    Called whenever signal_agent generates a setup card.

    Args:
        setup_card: dict with keys symbol, scan_type, composite_score,
                    entry_price, stop_price, target_2r, rr_ratio.
        was_approved: True if the human approved this for live trading.
    """
    db = SessionLocal()
    try:
        regime_data = get_latest_regime()

        shadow = ShadowTrade(
            signal_date=date_type.today(),
            symbol=setup_card.get("symbol", ""),
            signal_type=setup_card.get("scan_type", "PPC"),
            composite_score=setup_card.get("composite_score", 0),
            entry_price=setup_card.get("entry_price", 0),
            stop_price=setup_card.get("stop_price", 0),
            target_price=setup_card.get("target_2r", 0),
            rr_ratio=setup_card.get("rr_ratio", 0),
            regime=regime_data.get("regime", "UNKNOWN"),
            was_approved=was_approved,
        )

        db.add(shadow)
        db.commit()

        logger.info(
            f"Shadow trade recorded: {setup_card.get('symbol')} "
            f"(score={setup_card.get('composite_score')}, "
            f"approved={was_approved})"
        )

    except Exception as e:
        logger.error(f"Shadow trade recording failed: {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Update shadow exits
# ---------------------------------------------------------------------------

async def update_shadow_exits() -> None:
    """
    Check open shadow trades for exit conditions (stop or target hit).
    Called periodically to update paper P&L.
    """
    db = SessionLocal()
    try:
        open_shadows = (
            db.query(ShadowTrade)
            .filter(ShadowTrade.paper_exit_price.is_(None))
            .all()
        )

        if not open_shadows:
            return

        for shadow in open_shadows:
            _evaluate_shadow_exit(shadow)

        db.commit()

    except Exception as e:
        logger.error(f"Shadow exit update failed: {e}")
        db.rollback()
    finally:
        db.close()


def _evaluate_shadow_exit(shadow: ShadowTrade) -> None:
    """Check a single shadow trade against live price for stop/target."""
    try:
        ticker = yf.Ticker(f"{shadow.symbol}.NS")
        price = ticker.info.get("regularMarketPrice") or ticker.info.get(
            "previousClose", 0
        )
        price = float(price)
    except Exception as e:
        logger.warning(f"Price fetch failed for shadow {shadow.symbol}: {e}")
        return

    if price <= 0:
        return

    entry = shadow.entry_price or 0
    stop = shadow.stop_price or 0
    target = shadow.target_price or 0
    risk = entry - stop if entry and stop else 1

    # Stop hit
    if price <= stop:
        shadow.paper_exit_price = stop
        shadow.paper_exit_date = date_type.today()
        shadow.paper_pnl = stop - entry  # Negative for a loss
        shadow.paper_r_multiple = (
            shadow.paper_pnl / risk if risk > 0 else DEFAULT_R_ON_STOP
        )
        logger.info(
            f"Shadow {shadow.symbol}: stopped out @ {stop:.2f}"
        )
        return

    # Target hit (2R)
    if target and price >= target:
        shadow.paper_exit_price = target
        shadow.paper_exit_date = date_type.today()
        shadow.paper_pnl = target - entry
        shadow.paper_r_multiple = (
            shadow.paper_pnl / risk if risk > 0 else DEFAULT_R_ON_TARGET
        )
        logger.info(
            f"Shadow {shadow.symbol}: target hit @ {target:.2f}"
        )


# ---------------------------------------------------------------------------
# Comparison report
# ---------------------------------------------------------------------------

def get_shadow_comparison() -> dict:
    """
    Compare shadow portfolio vs live portfolio performance.
    Returns comparison metrics including human alpha.
    """
    db = SessionLocal()
    try:
        shadow_closed = (
            db.query(ShadowTrade)
            .filter(ShadowTrade.paper_exit_price.isnot(None))
            .all()
        )

        if not shadow_closed:
            return {
                "shadow_trades": 0,
                "message": (
                    "Insufficient shadow trades for comparison "
                    f"(need {MIN_SHADOW_TRADES_FOR_COMPARISON}+)"
                ),
            }

        # --- Shadow metrics ---
        shadow_r_values = [s.paper_r_multiple or 0 for s in shadow_closed]
        shadow_wins = sum(1 for r in shadow_r_values if r > 0)
        shadow_total_r = sum(shadow_r_values)
        shadow_count = len(shadow_closed)
        shadow_win_rate = shadow_wins / shadow_count if shadow_count else 0
        shadow_avg_r = shadow_total_r / shadow_count if shadow_count else 0

        # --- Approved vs skipped breakdown ---
        approved = [s for s in shadow_closed if s.was_approved]
        skipped = [s for s in shadow_closed if not s.was_approved]

        approved_win_rate = _win_rate_for_shadows(approved)
        skipped_win_rate = _win_rate_for_shadows(skipped)

        # --- Live trade metrics (gross_pnl-based R) ---
        live_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["CLOSED", "STOPPED"]))
            .all()
        )

        live_r_values = [t.r_multiple or 0 for t in live_trades]
        live_wins = sum(1 for r in live_r_values if r > 0)
        live_total_r = sum(live_r_values)
        live_count = len(live_trades)
        live_win_rate = live_wins / live_count if live_count else 0
        live_avg_r = live_total_r / live_count if live_count else 0

        # --- Human alpha ---
        alpha = live_avg_r - shadow_avg_r

        return {
            "shadow_trades": shadow_count,
            "shadow_win_rate": round(shadow_win_rate, 4),
            "shadow_avg_r": round(shadow_avg_r, 4),
            "shadow_total_r": round(shadow_total_r, 2),
            "approved_count": len(approved),
            "approved_win_rate": round(approved_win_rate, 4),
            "skipped_count": len(skipped),
            "skipped_win_rate": round(skipped_win_rate, 4),
            "live_trades": live_count,
            "live_win_rate": round(live_win_rate, 4),
            "live_avg_r": round(live_avg_r, 4),
            "live_total_r": round(live_total_r, 2),
            "human_alpha": round(alpha, 4),
            "verdict": (
                f"Human approval adds {alpha:+.2f}R alpha per trade"
                if alpha > 0
                else f"Shadow outperforms by {abs(alpha):.2f}R per trade"
            ),
            "sufficient_data": shadow_count >= MIN_SHADOW_TRADES_FOR_COMPARISON,
        }
    finally:
        db.close()


def _win_rate_for_shadows(shadows: list[ShadowTrade]) -> float:
    """Calculate win rate for a subset of shadow trades."""
    if not shadows:
        return 0.0
    wins = sum(1 for s in shadows if (s.paper_r_multiple or 0) > 0)
    return wins / len(shadows)


# ---------------------------------------------------------------------------
# Mark a shadow trade as approved (after human acts on it)
# ---------------------------------------------------------------------------

def mark_approved(shadow_id: int) -> bool:
    """
    Mark a shadow trade as approved after the human takes the live trade.
    Returns True if the update succeeded.
    """
    db = SessionLocal()
    try:
        shadow = db.query(ShadowTrade).filter(ShadowTrade.id == shadow_id).first()
        if not shadow:
            return False
        shadow.was_approved = True
        db.commit()
        logger.info(f"Shadow trade {shadow_id} ({shadow.symbol}) marked approved")
        return True
    except Exception as e:
        logger.error(f"Failed to mark shadow {shadow_id} approved: {e}")
        db.rollback()
        return False
    finally:
        db.close()
