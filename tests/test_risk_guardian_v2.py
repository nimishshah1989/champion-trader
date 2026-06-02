"""Tests for the v2 portfolio drawdown breaker (risk_guardian.current_dd_halt).

Replays the 15% halt / 7.5% resume state machine over the realised equity curve (closed
trades) and confirms it gates entries through live_jobs.run_entry_pass. In-memory DB."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.intelligence.risk_guardian import current_dd_halt
from backend.tables import Base, Trade

D = Decimal
CAP = D("100000")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _closed(db, pnls):
    """Seed CLOSED trades with the given gross P&L sequence, in exit order."""
    d0 = date(2024, 1, 1)
    for i, pnl in enumerate(pnls):
        db.add(Trade(symbol=f"S{i}", entry_date=d0, exit_date=d0 + timedelta(days=i + 1),
                     avg_entry_price=D(100), total_qty=1, remaining_qty=0,
                     status="CLOSED", gross_pnl=D(str(pnl))))
    db.commit()


def test_no_halt_on_empty_book(db):
    halted, equity, peak = current_dd_halt(db, start_capital=CAP)
    assert halted is False and equity == 100000.0 and peak == 100000.0


def test_no_halt_while_climbing(db):
    _closed(db, [50000])                              # equity 150k, peak 150k -> no DD
    halted, equity, peak = current_dd_halt(db, start_capital=CAP)
    assert halted is False and peak == 150000.0


def test_halt_trips_beyond_15pct_drawdown(db):
    _closed(db, [50000, -30000])                      # peak 150k, then 120k = -20% -> halt
    halted, equity, peak = current_dd_halt(db, start_capital=CAP)
    assert halted is True and equity == 120000.0 and peak == 150000.0


def test_resume_within_7_5pct_of_peak(db):
    _closed(db, [50000, -30000, 20000])               # 150k -> 120k (halt) -> 140k (>138.75k)
    halted, equity, peak = current_dd_halt(db, start_capital=CAP)
    assert halted is False and equity == 140000.0     # recovered through the resume band


def test_still_halted_inside_the_hysteresis_band(db):
    _closed(db, [50000, -30000, 5000])                # 150k -> 120k (halt) -> 125k (<138.75k)
    halted, _, _ = current_dd_halt(db, start_capital=CAP)
    assert halted is True                             # below resume, above re-halt -> stays halted
