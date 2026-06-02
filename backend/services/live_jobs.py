"""The v2 daily jobs — the thin orchestration the scheduler triggers (paper-live).

Each opens its own DB session + bar-store connection, delegates to a validated runtime
service, and returns a summary. Kept OUT of main.py so the live pipeline is unit-testable
without standing up FastAPI/APScheduler. The validated daily loop, post-close on the day's
Kite-adjusted bar (the same feed the backtest reads):

    17:30 ingest (corpus_updater) → 17:40 EXIT (close-based stop) → 17:45 ENTRY (breakouts)
    → 17:50 SCAN (refresh the watchlist for tomorrow);  next 09:15 → morning gap-down exits

Exit runs before entry so realised P&L and freed slots feed the entry sizing — exactly the
backtest's per-day order. In Phase-2 LIVE the ENTRY pass moves to the last 30 min on intraday
ticks (strategy_runtime.evaluate_live_entry); the validated decision logic is unchanged.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import date
from typing import Optional

from backend.config import settings
from backend.database import ScanResult, SessionLocal
from backend.services import entry_runtime, exit_runtime
from backend.services.autopilot import run_post_scan_automation
from backend.services.notifications import send_entry_fills, send_exit_fills
from backend.services.scanner_engine import run_v2_scan

logger = logging.getLogger(__name__)


def _notify(coro) -> None:
    """Best-effort Telegram send from a sync job (no-op when the bot isn't configured)."""
    try:
        asyncio.run(coro)
    except Exception as exc:                          # never let a notification break the job
        logger.warning(f"[v2 NOTIFY] skipped: {exc}")


def _store_con() -> sqlite3.Connection:
    """Open the Kite-adjusted bar store the live jobs read (read-only intent)."""
    return sqlite3.connect(settings.bars_db_path)


def _universe(con: sqlite3.Connection) -> list[str]:
    """The live universe = every symbol with ingested bars in the store."""
    return [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]


def run_daily_scan(scan_date: Optional[date] = None,
                   symbols: Optional[list[str]] = None) -> dict:
    """Post-close: v2 SETUP scan over the store → persist ScanResult rows → populate watchlist."""
    scan_date = scan_date or date.today()
    con = _store_con()
    db = SessionLocal()
    try:
        universe = symbols if symbols is not None else _universe(con)
        rows = run_v2_scan(con, universe, scan_date, as_of=scan_date)   # leakage-safe
        for row in rows:
            db.query(ScanResult).filter(
                ScanResult.scan_date == row["scan_date"],
                ScanResult.symbol == row["symbol"],
                ScanResult.scan_type == row["scan_type"],
            ).delete()
            db.add(ScanResult(**row))
        db.commit()
        added = run_post_scan_automation().get("watchlist_added", 0)
        logger.info(f"[v2 SCAN] {len(rows)} setups for {scan_date}; +{added} to watchlist")
        return {"setups": len(rows), "watchlist_added": added}
    except Exception as exc:
        logger.error(f"[v2 SCAN] failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()
        con.close()


def run_entry_pass(as_of: Optional[date] = None,
                   symbols: Optional[list[str]] = None) -> dict:
    """Post-close: open v2 trades for watchlist names that broke out on the day's bar."""
    from backend.intelligence.risk_guardian import current_dd_halt

    con = _store_con()
    db = SessionLocal()
    try:
        halted, _, _ = current_dd_halt(db)          # 15% DD breaker gates new entries
        summary = entry_runtime.run_entries(db, con, as_of=as_of, symbols=symbols,
                                            halted=halted)
        logger.info(f"[v2 ENTRY] checked {summary['checked']}, entered {summary['entered']}, "
                    f"blocked {summary['blocked']}")
        if summary.get("opened"):
            _notify(send_entry_fills(summary["opened"]))
        return summary
    except Exception as exc:
        logger.error(f"[v2 ENTRY] failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()
        con.close()


def run_exit_pass(as_of: Optional[date] = None) -> dict:
    """Post-close: close-based 5xATR chandelier exit on open trades (else ratchet + persist)."""
    con = _store_con()
    db = SessionLocal()
    try:
        summary = exit_runtime.run_eod_exits(db, con, as_of=as_of)
        logger.info(f"[v2 EXIT] checked {summary['checked']}, exited {summary['exited']}, "
                    f"trailed {summary['trailed']}")
        if summary.get("closed"):
            _notify(send_exit_fills(summary["closed"]))
        return summary
    except Exception as exc:
        logger.error(f"[v2 EXIT] failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()
        con.close()


def run_morning_gap_pass(as_of: Optional[date] = None) -> dict:
    """09:15: exit any open position that gaps open below its stop."""
    con = _store_con()
    db = SessionLocal()
    try:
        summary = exit_runtime.run_morning_gap_exits(db, con, as_of=as_of)
        logger.info(f"[v2 GAP] checked {summary['checked']}, exited {summary['exited']}")
        if summary.get("closed"):
            _notify(send_exit_fills(summary["closed"]))
        return summary
    except Exception as exc:
        logger.error(f"[v2 GAP] failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()
        con.close()
