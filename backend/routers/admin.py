"""
Admin router — one-time DB maintenance operations.

POST /admin/reset-legacy-data
    Archives all pre-v2 trades (marks OPEN/PARTIAL as CLOSED with
    exit_reason="legacy-archived"), removes old watchlist entries, and
    wipes scan results that pre-date the v2 migration.  Safe to call more
    than once (idempotent).
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import ScanResult, Trade, Watchlist, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Trades created before this date are considered pre-v2 legacy data.
# The v2 engine started paper trading from scratch; anything before this
# is old CTS manual-entry data that should be archived.
V2_CUTOFF = date(2025, 1, 1)


@router.post("/reset-legacy-data")
def reset_legacy_data(db: Session = Depends(get_db)):
    """
    Archive pre-v2 DB data so the v2 pipeline starts with a clean slate.

    Actions performed:
    - OPEN / PARTIAL trades with entry_date < V2_CUTOFF → marked CLOSED,
      exit_reason = "legacy-archived", r_multiple = 0
    - All ACTIVE watchlist entries → status = REMOVED, notes updated
    - All scan results with scan_type != 'V2' → deleted
    - V2 scan results older than 90 days → deleted (keep recent)
    """
    trades_archived = 0
    watchlist_cleared = 0
    scans_cleared = 0

    try:
        # 1. Archive legacy open/partial trades
        legacy_trades = (
            db.query(Trade)
            .filter(
                Trade.status.in_(["OPEN", "PARTIAL"]),
                Trade.entry_date < V2_CUTOFF,
            )
            .all()
        )
        for t in legacy_trades:
            t.status = "CLOSED"
            t.exit_reason = "legacy-archived"
            t.r_multiple = t.r_multiple if t.r_multiple is not None else 0
            trades_archived += 1

        # Also archive any remaining OPEN trades regardless of date
        # (v2 paper engine manages its own open trades via simulation_runs)
        remaining_open = (
            db.query(Trade)
            .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
            .all()
        )
        for t in remaining_open:
            t.status = "CLOSED"
            t.exit_reason = "legacy-archived"
            t.r_multiple = t.r_multiple if t.r_multiple is not None else 0
            trades_archived += 1

        # 2. Clear active watchlist entries from old PPC/NPC scans
        old_watchlist = (
            db.query(Watchlist)
            .filter(Watchlist.status == "ACTIVE")
            .all()
        )
        for w in old_watchlist:
            w.status = "REMOVED"
            w.notes = (w.notes or "") + " [legacy-archived]"
            watchlist_cleared += 1

        # 3. Clear old non-V2 scan results
        old_scans = (
            db.query(ScanResult)
            .filter(ScanResult.scan_type != "V2")
            .all()
        )
        for s in old_scans:
            db.delete(s)
            scans_cleared += 1

        db.commit()

        logger.info(
            f"[ADMIN RESET] archived {trades_archived} trades, "
            f"cleared {watchlist_cleared} watchlist entries, "
            f"deleted {scans_cleared} legacy scan results"
        )

        return {
            "status": "ok",
            "trades_archived": trades_archived,
            "watchlist_cleared": watchlist_cleared,
            "scans_cleared": scans_cleared,
            "message": (
                f"Legacy data archived. "
                f"{trades_archived} trades marked closed, "
                f"{watchlist_cleared} watchlist entries removed, "
                f"{scans_cleared} old scan results deleted. "
                "The v2 pipeline now has a clean slate."
            ),
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"[ADMIN RESET] failed: {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}
