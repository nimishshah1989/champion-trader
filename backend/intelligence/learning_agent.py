"""
learning_agent.py -- Post-mortem generator and Corpus C writer.

Triggered when a trade is closed. Polls every 30 minutes for newly
closed trades that don't yet have a post-mortem in Corpus C.

Post-mortem fields:
  - trade summary, signal quality, regime at entry
  - expected vs actual R, stop behaviour, exit quality
  - Claude-generated 2-sentence learning note

After generating:
  1. Write to Corpus C via rag_engine
  2. Update signal_attribution table
  3. Flag underperforming signal x regime combos
"""

from __future__ import annotations

import logging
from datetime import date as date_cls, datetime

from anthropic import Anthropic

from backend.config import settings
from backend.database import (
    RegimeLog,
    SessionLocal,
    SignalAttribution,
    Trade,
)
from backend.intelligence.rag_engine import ingest_document

logger = logging.getLogger(__name__)

# Track which trade IDs have already been post-mortem'd this session
_processed_trade_ids: set[int] = set()

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------
EXIT_R_EXTREME_EXTENSION = 12.0
EXIT_R_GREAT_EXTENSION = 8.0
EXIT_R_NORMAL_EXTENSION = 4.0
EXIT_R_MATHEMATICAL = 2.0
UNDERPERFORMANCE_MIN_TRADES = 20
UNDERPERFORMANCE_WIN_RATE_THRESHOLD = 0.40
LEARNING_NOTE_MAX_TOKENS = 100


async def process_closed_trades() -> None:
    """
    Scan for closed trades without post-mortems and generate them.
    Called by APScheduler every 30 minutes during market hours.
    """
    db = SessionLocal()
    try:
        closed_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["CLOSED", "STOPPED"]))
            .all()
        )

        new_closures = [
            t for t in closed_trades if t.id not in _processed_trade_ids
        ]

        if not new_closures:
            return

        logger.info(f"Processing {len(new_closures)} new trade closures")

        for trade in new_closures:
            try:
                await _generate_post_mortem(db, trade)
                _processed_trade_ids.add(trade.id)
            except Exception as e:
                logger.error(f"Post-mortem failed for trade {trade.id}: {e}")

        db.commit()

    except Exception as e:
        logger.error(f"Learning agent error: {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Post-mortem generation
# ---------------------------------------------------------------------------

async def _generate_post_mortem(db, trade: Trade) -> None:
    """Generate a full post-mortem for a closed trade."""
    entry_price = float(trade.avg_entry_price or 0)
    exit_price = float(trade.exit_price or 0)
    trp_pct = float(trade.trp_at_entry or 0)
    trp_value = entry_price * (trp_pct / 100) if trp_pct else 0
    r_multiple = float(trade.r_multiple or 0)
    pnl = float(trade.gross_pnl or 0)

    # Regime at entry date
    regime_at_entry = _lookup_regime_at_entry(db, trade.entry_date)

    # Exit quality classification
    exit_quality = _classify_exit_quality(r_multiple, trade.status)

    # Hold duration
    hold_days = _calculate_hold_days(trade.entry_date, trade.exit_date)

    # Signal type from notes or setup_type
    signal_type = _infer_signal_type(trade)

    # Claude-generated learning note
    learning_note = await _generate_learning_note(
        trade, regime_at_entry, exit_quality, hold_days
    )

    # Build post-mortem text
    post_mortem = (
        f"TRADE POST-MORTEM: {trade.symbol}\n"
        f"Date: {trade.entry_date} -> {trade.exit_date} ({hold_days} days)\n"
        f"Signal: {signal_type} | Regime: {regime_at_entry}\n"
        f"Entry: {entry_price:.2f} | Exit: {exit_price:.2f}\n"
        f"P&L: {pnl:,.0f} | R-multiple: {r_multiple:.2f}\n"
        f"Exit Quality: {exit_quality}\n"
        f"TRP%: {trp_pct:.2f} | Stop: {trade.sl_price:.2f}\n"
        f"Status: {trade.status}\n"
        f"Learning: {learning_note}"
    )

    # 1. Write to Corpus C
    ingest_document(
        text=post_mortem,
        metadata={
            "corpus": "c",
            "date": str(
                trade.exit_date or datetime.now().strftime("%Y-%m-%d")
            ),
            "type": "post_mortem",
            "symbol": trade.symbol,
            "signal_type": signal_type,
            "regime": regime_at_entry,
            "r_multiple": str(r_multiple),
            "trade_id": str(trade.id),
        },
        corpus="corpus_c",
    )

    # 2. Update signal attribution
    _update_attribution(db, signal_type, regime_at_entry, r_multiple)

    # 3. Flag underperforming combos
    _check_underperformance(db, signal_type, regime_at_entry)

    logger.info(
        f"Post-mortem generated for {trade.symbol} "
        f"(R={r_multiple:.2f}, {exit_quality})"
    )


# ---------------------------------------------------------------------------
# Helper: exit quality
# ---------------------------------------------------------------------------

def _classify_exit_quality(r_multiple: float, status: str | None) -> str:
    """Map an R-multiple to a human-readable exit quality label."""
    if r_multiple >= EXIT_R_EXTREME_EXTENSION:
        return "EXTREME_EXTENSION"
    if r_multiple >= EXIT_R_GREAT_EXTENSION:
        return "GREAT_EXTENSION"
    if r_multiple >= EXIT_R_NORMAL_EXTENSION:
        return "NORMAL_EXTENSION"
    if r_multiple >= EXIT_R_MATHEMATICAL:
        return "MATHEMATICAL_EXIT"
    if r_multiple > 0:
        return "PARTIAL_WIN"
    if status == "STOPPED":
        return "STOPPED_OUT"
    return "LOSS"


# ---------------------------------------------------------------------------
# Helper: regime lookup
# ---------------------------------------------------------------------------

def _lookup_regime_at_entry(db, entry_date) -> str:
    """Get the regime classification that was active on entry_date."""
    if not entry_date:
        return "UNKNOWN"
    try:
        regime_entry = (
            db.query(RegimeLog)
            .filter(RegimeLog.regime_date <= entry_date)
            .order_by(RegimeLog.regime_date.desc())
            .first()
        )
        if regime_entry:
            return regime_entry.regime
    except Exception:
        pass
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Helper: hold days
# ---------------------------------------------------------------------------

def _calculate_hold_days(entry_date, exit_date) -> int:
    """Calculate the number of calendar days from entry to exit."""
    if not entry_date or not exit_date:
        return 0
    try:
        entry_d = (
            entry_date
            if isinstance(entry_date, date_cls)
            else date_cls.fromisoformat(str(entry_date))
        )
        exit_d = (
            exit_date
            if isinstance(exit_date, date_cls)
            else date_cls.fromisoformat(str(exit_date))
        )
        return (exit_d - entry_d).days
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Helper: signal type inference
# ---------------------------------------------------------------------------

def _infer_signal_type(trade: Trade) -> str:
    """
    Infer signal type from trade.setup_type or trade.entry_notes.
    Falls back to 'PPC' as the most common scan type.
    """
    # Prefer the explicit setup_type field
    setup = (trade.setup_type or "").upper()
    if "NPC" in setup:
        return "NPC"
    if "CONTRACTION" in setup:
        return "CONTRACTION"
    if "PPC" in setup:
        return "PPC"

    # Fallback: scan entry_notes
    notes = (trade.entry_notes or "").upper()
    if "NPC" in notes:
        return "NPC"
    if "CONTRACTION" in notes:
        return "CONTRACTION"

    return "PPC"


# ---------------------------------------------------------------------------
# Claude learning note
# ---------------------------------------------------------------------------

async def _generate_learning_note(
    trade: Trade,
    regime: str,
    exit_quality: str,
    hold_days: int,
) -> str:
    """Generate a 2-sentence learning insight via Claude."""
    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.autooptimize_model,
            max_tokens=LEARNING_NOTE_MAX_TOKENS,
            system="You are a trading journal analyst. Write exactly 2 sentences.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Trade: {trade.symbol}, {regime} regime, "
                        f"R={trade.r_multiple:.2f}, held {hold_days} days, "
                        f"exit: {exit_quality}. "
                        f"What is the key learning from this trade?"
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Learning note generation failed: {e}")
        return f"Trade closed at {exit_quality} in {regime} regime."


# ---------------------------------------------------------------------------
# Signal attribution
# ---------------------------------------------------------------------------

def _update_attribution(
    db, signal_type: str, regime: str, r_multiple: float
) -> None:
    """Update the signal_attribution table with new trade outcome."""
    try:
        attr = (
            db.query(SignalAttribution)
            .filter(
                SignalAttribution.signal_type == signal_type,
                SignalAttribution.regime == regime,
            )
            .first()
        )

        is_win = r_multiple > 0

        if attr:
            attr.trade_count = (attr.trade_count or 0) + 1
            attr.win_count = (attr.win_count or 0) + (1 if is_win else 0)
            attr.total_r = (attr.total_r or 0) + r_multiple
            attr.avg_r = (
                attr.total_r / attr.trade_count
                if attr.trade_count > 0
                else 0
            )
            attr.win_rate = (
                attr.win_count / attr.trade_count
                if attr.trade_count > 0
                else 0
            )
        else:
            attr = SignalAttribution(
                signal_type=signal_type,
                regime=regime,
                trade_count=1,
                win_count=1 if is_win else 0,
                total_r=r_multiple,
                avg_r=r_multiple,
                win_rate=1.0 if is_win else 0.0,
            )
            db.add(attr)

    except Exception as e:
        logger.error(f"Attribution update failed: {e}")


def _check_underperformance(db, signal_type: str, regime: str) -> None:
    """
    Flag if a signal x regime combo has <40% win rate over 20+ trades.
    Logged as a warning for the next AutoOptimize cycle to pick up.
    """
    try:
        attr = (
            db.query(SignalAttribution)
            .filter(
                SignalAttribution.signal_type == signal_type,
                SignalAttribution.regime == regime,
            )
            .first()
        )

        if (
            attr
            and (attr.trade_count or 0) >= UNDERPERFORMANCE_MIN_TRADES
            and (attr.win_rate or 0) < UNDERPERFORMANCE_WIN_RATE_THRESHOLD
        ):
            logger.warning(
                f"UNDERPERFORMING: {signal_type} x {regime} -- "
                f"win rate {attr.win_rate:.0%} over {attr.trade_count} trades. "
                f"Priority re-optimisation recommended."
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API for router / frontend
# ---------------------------------------------------------------------------

def get_attribution_table() -> list[dict]:
    """Get full signal attribution table for API / frontend."""
    db = SessionLocal()
    try:
        rows = db.query(SignalAttribution).all()
        return [
            {
                "signal_type": r.signal_type,
                "regime": r.regime,
                "trade_count": r.trade_count,
                "win_count": r.win_count,
                "total_r": round(r.total_r or 0, 2),
                "avg_r": round(r.avg_r or 0, 2),
                "win_rate": round(r.win_rate or 0, 4),
            }
            for r in rows
        ]
    finally:
        db.close()
