"""Integration tests for the wired v2 daily jobs (live_jobs) — the seam main.py schedules.

Repoints the shared SessionLocal at a temp DB (so the jobs + the autopilot watchlist glue
share one DB) and the bar store at the real cache. Proves: the scan job persists V2 setups
and the post-scan glue accepts v2 avg_trp into the watchlist; every pass is a robust no-op
on an empty book. The detailed entry/exit logic is covered by test_entry_runtime /
test_exit_runtime. Cache-backed tests skip if champion_cache.sqlite is absent."""
import os
import sqlite3
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from backend.engine.backtest_fast import load_bars
from backend.engine.precompute import precompute_features
from backend.engine.runtime.config import RISK_V2
from backend.engine.runtime.signal_service import WARMUP, context_from_df, setup_at
from backend.services import scanner_engine

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
needs_cache = pytest.mark.skipif(not os.path.exists(CACHE), reason="champion_cache.sqlite not present")


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Repoint the shared SessionLocal at a fresh temp DB (restored on teardown)."""
    from backend import database
    from backend.config import settings
    from backend.tables import Base

    engine = create_engine(f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(engine)
    database.SessionLocal.configure(bind=engine)
    monkeypatch.setattr(settings, "bars_db_path", CACHE)
    yield engine
    database.SessionLocal.configure(bind=database.engine)


def _find_setup(con, *, floor_cr, max_symbols=150):
    symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
    for sym in symbols[:max_symbols]:
        bars = load_bars(con, sym)
        if len(bars) < 300:
            continue
        ctx = context_from_df(bars, precompute_features(bars))
        for j in range(len(bars) - 1, max(WARMUP - 1, len(bars) - 500), -1):
            if setup_at(ctx, j) is not None and scanner_engine._turnover_cr(bars[: j + 1]) >= floor_cr:
                return sym, bars[j].date
    return None, None


@needs_cache
def test_run_daily_scan_persists_a_v2_setup(temp_db):
    from backend.database import ScanResult
    from backend.services import live_jobs

    con = sqlite3.connect(CACHE)
    sym, d = _find_setup(con, floor_cr=RISK_V2.liquidity_floor_cr)
    con.close()
    assert sym is not None, "no v2 setup found in the sampled cache symbols"

    out = live_jobs.run_daily_scan(scan_date=d, symbols=[sym])
    assert out["setups"] == 1
    db = live_jobs.SessionLocal()
    try:
        rows = (db.query(ScanResult)
                .filter(ScanResult.symbol == sym, ScanResult.scan_type == "V2").all())
        assert len(rows) == 1 and rows[0].watchlist_bucket == "READY"
    finally:
        db.close()


def test_post_scan_populate_accepts_v2_avg_trp(temp_db):
    """The post-scan glue must add v2 rows (which carry avg_trp, not trp) to the watchlist."""
    from backend.database import ScanResult, Watchlist
    from backend.services import live_jobs
    from backend.services.autopilot import run_post_scan_automation

    db = live_jobs.SessionLocal()
    try:
        db.add(ScanResult(scan_date=date.today(), symbol="TESTV2", scan_type="V2",
                          close_price=Decimal("100"), volume=10000, avg_trp=Decimal("3.0"),
                          stage="S2", has_min_20_bar_base=True, adt=Decimal("5e7"),
                          passes_liquidity_filter=True, watchlist_bucket="READY",
                          trigger_level=Decimal("105")))
        db.commit()
    finally:
        db.close()

    out = run_post_scan_automation()
    assert out.get("watchlist_added") == 1
    db = live_jobs.SessionLocal()
    try:
        wl = db.query(Watchlist).filter(Watchlist.symbol == "TESTV2").all()
        assert len(wl) == 1 and wl[0].bucket == "READY"
    finally:
        db.close()


def test_run_daily_ingest_skips_when_kite_unconfigured(monkeypatch):
    from backend.config import settings
    from backend.services import live_jobs

    monkeypatch.setattr(settings, "kite_api_key", "")
    monkeypatch.setattr(settings, "kite_access_token", "")
    assert live_jobs.run_daily_ingest() == {"skipped": "kite-not-configured"}


@needs_cache
def test_jobs_are_robust_noops_on_empty_db(temp_db):
    from backend.services import live_jobs

    # no watchlist, no open trades -> every pass is a clean no-op (no error raised)
    assert live_jobs.run_entry_pass(as_of=date(2024, 1, 2)).get("entered") == 0
    assert live_jobs.run_exit_pass(as_of=date(2024, 1, 2)).get("exited") == 0
    assert live_jobs.run_morning_gap_pass(as_of=date(2024, 1, 2)).get("exited") == 0
