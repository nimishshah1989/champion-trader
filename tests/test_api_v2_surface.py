"""API-surface tests for the v2 fields the frontend dashboard reads.

Two thin contract guards:
  1. TradeResponse serialises the v2 trailing-stop + attribution columns (so the trades
     UI can show current_stop/highest_high/atr_at_entry + signal_type/regime/avg_trp/version).
  2. GET /api/intelligence/risk/status carries the drawdown-breaker block (15%/7.5%) so the
     UI can show how close the portfolio is to halting new entries — not just a freeze flag.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine


def test_trade_response_exposes_v2_trail_and_attribution():
    """The 8 v2 columns on the Trade table round-trip through TradeResponse."""
    from backend.models.trade import TradeResponse
    from backend.tables import Trade

    t = Trade(
        id=1, symbol="ASTERDM", entry_date=date(2024, 1, 1), status="OPEN",
        avg_entry_price=Decimal("601"), total_qty=131, sl_price=Decimal("581.9"),
        current_stop=Decimal("590.5"), highest_high=Decimal("640.0"),
        atr_at_entry=Decimal("12.3456"), signal_type="S2", regime_at_entry="bull",
        volume_ratio_at_entry=Decimal("2.4"), avg_trp_at_entry=Decimal("3.18"),
        strategy_version="v2",
    )
    r = TradeResponse.model_validate(t)

    assert r.current_stop == Decimal("590.5")
    assert r.highest_high == Decimal("640.0")
    assert r.atr_at_entry == Decimal("12.3456")
    assert r.signal_type == "S2"
    assert r.regime_at_entry == "bull"
    assert r.volume_ratio_at_entry == Decimal("2.4")
    assert r.avg_trp_at_entry == Decimal("3.18")
    assert r.strategy_version == "v2"


@pytest.mark.asyncio
async def test_risk_status_includes_drawdown_block(tmp_path, monkeypatch):
    """risk/status replays the realised equity curve and reports the breaker state."""
    from backend import database
    from backend.config import settings
    from backend.tables import Base, Trade
    from backend.routers.intelligence import risk_status

    engine = create_engine(f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(engine)
    database.SessionLocal.configure(bind=engine)
    monkeypatch.setattr(settings, "paper_capital", 100000)  # deterministic start capital
    try:
        s = database.SessionLocal()
        d0 = date(2024, 1, 1)
        for i, pnl in enumerate([50000, -30000]):  # 100k -> 150k (peak) -> 120k = -20% DD
            s.add(Trade(symbol=f"S{i}", entry_date=d0, exit_date=d0 + timedelta(days=i + 1),
                        avg_entry_price=Decimal("100"), total_qty=1, remaining_qty=0,
                        status="CLOSED", gross_pnl=Decimal(str(pnl))))
        s.commit()
        s.close()

        resp = await risk_status()
        dd = resp["drawdown"]
        assert dd["halted"] is True                       # -20% is past the 15% halt
        assert dd["peak"] == 150000.0 and dd["equity"] == 120000.0
        assert round(dd["drawdown_pct"], 1) == 20.0
        assert dd["halt_threshold_pct"] == 15.0
        assert dd["resume_threshold_pct"] == 7.5
    finally:
        database.SessionLocal.configure(bind=database.engine)


def test_scanner_run_uses_the_v2_scan(tmp_path, monkeypatch):
    """POST /scanner/run drives the validated v2 scan and returns its V2 rows.

    run_daily_scan is the one brain (it reads the cache); here we stub it to persist a
    V2 row so the test stays fast/cache-free, and assert the endpoint returns exactly
    the scan_type="V2" rows for the requested date.
    """
    from backend import database
    from backend.tables import Base, ScanResult
    from backend.models.scan_result import ScanRequest
    from backend.routers import scanner
    from backend.services import live_jobs

    engine = create_engine(f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(engine)
    database.SessionLocal.configure(bind=engine)
    try:
        def fake_daily_scan(scan_date=None, symbols=None):
            s = database.SessionLocal()
            s.add(ScanResult(scan_date=scan_date, symbol="ASTERDM", scan_type="V2",
                             avg_trp=Decimal("3.18"), stage="S2", watchlist_bucket="READY",
                             trigger_level=Decimal("601")))
            s.commit()
            s.close()
            return {"setups": 1, "watchlist_added": 1}

        monkeypatch.setattr(live_jobs, "run_daily_scan", fake_daily_scan)

        db = database.SessionLocal()
        rows = scanner.run_scan(ScanRequest(scan_type="V2", date=date(2024, 6, 2)), db=db)
        db.close()

        assert len(rows) == 1
        assert rows[0].scan_type == "V2" and rows[0].symbol == "ASTERDM"
        assert rows[0].stage == "S2" and rows[0].watchlist_bucket == "READY"
    finally:
        database.SessionLocal.configure(bind=database.engine)


def test_scanner_run_returns_empty_when_no_setups(tmp_path, monkeypatch):
    """A scan that finds nothing returns an empty list, not an error."""
    from backend import database
    from backend.tables import Base
    from backend.models.scan_result import ScanRequest
    from backend.routers import scanner
    from backend.services import live_jobs

    engine = create_engine(f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(engine)
    database.SessionLocal.configure(bind=engine)
    try:
        monkeypatch.setattr(live_jobs, "run_daily_scan",
                            lambda *a, **k: {"setups": 0, "watchlist_added": 0})
        db = database.SessionLocal()
        rows = scanner.run_scan(ScanRequest(scan_type="V2", date=date(2024, 6, 2)), db=db)
        db.close()
        assert rows == []
    finally:
        database.SessionLocal.configure(bind=database.engine)


def test_scanner_run_raises_500_on_scan_error(tmp_path, monkeypatch):
    """A scan failure (e.g. missing bar store) surfaces as HTTP 500, not a silent pass."""
    from fastapi import HTTPException
    from backend import database
    from backend.tables import Base
    from backend.models.scan_result import ScanRequest
    from backend.routers import scanner
    from backend.services import live_jobs

    engine = create_engine(f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(engine)
    database.SessionLocal.configure(bind=engine)
    try:
        monkeypatch.setattr(live_jobs, "run_daily_scan",
                            lambda *a, **k: {"error": "bar store missing"})
        db = database.SessionLocal()
        with pytest.raises(HTTPException) as ei:
            scanner.run_scan(ScanRequest(scan_type="V2"), db=db)
        db.close()
        assert ei.value.status_code == 500 and "bar store missing" in ei.value.detail
    finally:
        database.SessionLocal.configure(bind=database.engine)


def test_config_drops_dead_dhan_keys_keeps_kite():
    """Dhan is deleted (broker = Kite): the dead config keys are gone, Kite's remain."""
    from backend.config import settings
    assert not hasattr(settings, "dhan_client_id")
    assert not hasattr(settings, "dhan_access_token")
    assert hasattr(settings, "kite_api_key") and hasattr(settings, "kite_access_token")
