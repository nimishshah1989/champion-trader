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
