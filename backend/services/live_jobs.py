"""The v2 daily jobs — the thin orchestration the scheduler triggers (paper-live).

Each opens its own DB session + bar-store connection, delegates to a validated runtime
service, and returns a summary. The validated daily loop, post-close on the day's
Kite-adjusted bar:

    17:30 ingest → 17:40 EXIT (close-based chandelier) → 17:45 ENTRY (breakouts)
    → 17:50 SCAN (refresh the watchlist for tomorrow);  next 09:15 → morning gap-down exits

Exit runs before entry so realised P&L and freed slots feed the entry sizing — exactly the
backtest's per-day order.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import date
from decimal import Decimal
from typing import Optional

from backend.config import settings
from backend.database import ScanResult, SessionLocal, Trade, Watchlist
from backend.engine import market_store
from backend.services import entry_runtime, exit_runtime
from backend.services.notifications import send_entry_fills, send_exit_fills
from backend.services.scanner_engine import run_v2_scan

logger = logging.getLogger(__name__)

_INDICES = ("NIFTY 50", "NIFTY 500")
_MIN_TRP = Decimal("2.0")


def _populate_watchlist_from_scan(db, scan_date: date) -> int:
    """Read today's scan results and auto-add qualifying stocks to the watchlist."""
    results = db.query(ScanResult).filter(ScanResult.scan_date == scan_date).all()
    if not results:
        return 0

    existing = {
        w.symbol for w in db.query(Watchlist).filter(Watchlist.status == "ACTIVE").all()
    }
    open_trades = {
        t.symbol for t in db.query(Trade).filter(Trade.status.in_(["OPEN", "PARTIAL"])).all()
    }

    added = 0
    for scan in results:
        if scan.symbol in existing or scan.symbol in open_trades:
            continue
        if scan.watchlist_bucket not in ("READY", "NEAR"):
            continue
        if not scan.passes_liquidity_filter:
            continue
        trp_src = scan.avg_trp if scan.avg_trp is not None else scan.trp
        if not trp_src or Decimal(str(trp_src)) < _MIN_TRP:
            continue
        trp_val = Decimal(str(trp_src))
        db.add(Watchlist(
            symbol=scan.symbol,
            added_date=scan_date,
            bucket=scan.watchlist_bucket,
            stage=scan.stage,
            base_days=scan.base_days,
            base_quality=scan.base_quality,
            wuc_types=scan.wuc_type,
            trigger_level=scan.trigger_level,
            planned_entry_price=scan.trigger_level,
            planned_sl_pct=trp_val,
            status="ACTIVE",
            notes=f"Auto-added from {scan.scan_type} scan on {scan_date}",
        ))
        existing.add(scan.symbol)
        added += 1

    if added:
        db.commit()
    logger.info(f"[v2 SCAN] +{added} to watchlist from {scan_date} scan")
    return added


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


def run_daily_ingest(*, cache_path: Optional[str] = None,
                     start: date = date(2015, 1, 1)) -> dict:
    """Post-close: refresh the Kite-adjusted bar store the v2 pipeline reads (runs first).

    Incremental — each symbol fetches only bars after its last stored date. A safe no-op when
    Kite isn't configured (dev / before the daily token refresh), so the schedule never errors.
    """
    if not (settings.kite_api_key and settings.kite_access_token):
        logger.warning("[v2 INGEST] Kite not configured — skipping bar-store refresh")
        return {"skipped": "kite-not-configured"}
    from backend.engine.kite_data import KiteHistoricalAdapter

    adapter = KiteHistoricalAdapter(settings.kite_api_key, settings.kite_access_token)
    con = sqlite3.connect(cache_path or settings.bars_db_path)
    today = date.today()
    new_bars = missing = failed = 0
    try:
        market_store.ensure_schema(con)
        for sym in _universe(con):
            try:
                new_bars += market_store.ingest_symbol(con, adapter, sym, start=start,
                                                        end=today, as_of=today)
            except KeyError:                          # symbol not in Kite -> mark done, skip on resume
                con.execute("insert or replace into done values(?,?)", (sym, 0))
                con.commit()
                missing += 1
            except Exception as exc:
                logger.warning(f"[v2 INGEST] {sym}: {exc}")
                failed += 1
        for code in _INDICES:
            try:
                market_store.ingest_index(con, adapter, code, start=start, end=today, as_of=today)
            except Exception as exc:
                logger.warning(f"[v2 INGEST] index {code}: {exc}")
    finally:
        con.close()
    logger.info(f"[v2 INGEST] +{new_bars:,} bars, {missing} not-in-kite, {failed} failed")
    return {"new_bars": new_bars, "missing": missing, "failed": failed}


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
        added = _populate_watchlist_from_scan(db, scan_date)
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
