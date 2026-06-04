"""
Admin router — system setup and one-time DB maintenance operations.

POST /admin/reset-legacy-data     Archive pre-v2 stale trades/watchlist/scans
POST /admin/run-ingest            Trigger Kite bar ingest in background thread
GET  /admin/bar-store-status      How many symbols/bars are in the bar store
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import ScanResult, Trade, Watchlist, get_db
from backend.engine import market_store

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


# ---------------------------------------------------------------------------
# Bar store status
# ---------------------------------------------------------------------------

@router.get("/bar-store-status")
def bar_store_status():
    """How many symbols and bars are in the Kite-adjusted bar store."""
    con = sqlite3.connect(settings.bars_db_path)
    try:
        market_store.ensure_schema(con)
        symbols_done, total_bars = con.execute(
            "select count(*), coalesce(sum(n),0) from done where n>0"
        ).fetchone()
        latest_date = con.execute("select max(date) from bars").fetchone()[0]
        return {
            "symbols_with_bars": symbols_done,
            "total_bars": int(total_bars),
            "latest_bar_date": latest_date,
            "ready_for_scan": symbols_done > 0,
        }
    except Exception as exc:
        return {"symbols_with_bars": 0, "total_bars": 0, "latest_bar_date": None,
                "ready_for_scan": False, "error": str(exc)}
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Run ingest on-demand
# ---------------------------------------------------------------------------

_ingest_running = False   # simple lock — one ingest at a time


@router.post("/run-ingest")
def run_ingest_now(quick: bool = Query(True, description="True=last 18 months (fast); False=full backfill from 2015")):
    """Start a Kite bar ingest in a background thread. Returns immediately.

    quick=True (default): fetches the last ~500 days only (~7 minutes for
    1 300 symbols). Sufficient for the v2 scanner which needs ~6 months of
    history.  quick=False: full backfill from 2015 (use only for backtesting).

    Requires KITE_API_KEY + KITE_ACCESS_TOKEN to be set in the environment.
    """
    global _ingest_running

    if not settings.kite_api_key or not settings.kite_access_token:
        return {
            "status": "error",
            "message": "KITE_API_KEY or KITE_ACCESS_TOKEN not configured. Complete Kite auth first.",
        }

    if _ingest_running:
        return {"status": "already_running", "message": "Ingest is already running. Check bar-store-status for progress."}

    start = date.today() - timedelta(days=500) if quick else date(2015, 1, 1)

    def _run():
        global _ingest_running
        _ingest_running = True
        try:
            from backend.services.live_jobs import run_daily_ingest
            result = run_daily_ingest(start=start)
            logger.info(f"[ADMIN INGEST] complete: {result}")
        except Exception as exc:
            logger.error(f"[ADMIN INGEST] failed: {exc}", exc_info=True)
        finally:
            _ingest_running = False

    t = threading.Thread(target=_run, daemon=True, name="admin-ingest")
    t.start()

    return {
        "status": "started",
        "quick": quick,
        "start_date": start.isoformat(),
        "message": (
            f"Kite ingest started in background (start={start}, ~1 300 symbols). "
            "Poll GET /admin/bar-store-status to watch progress. "
            "Takes ~7–10 minutes for a quick ingest."
        ),
    }
