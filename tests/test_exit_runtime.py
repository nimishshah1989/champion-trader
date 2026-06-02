"""Tests for the post-close v2 exit job (exit_runtime) — in-memory DB + market store.

Covers the two live moments (close-below exit, 09:15 gap exit), the ratchet-and-persist
hold path, and self-healing the trail from sl_price/avg_entry_price on a legacy trade."""
import sqlite3
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.engine import market_store
from backend.engine.kite_data import Bar
from backend.services import exit_runtime
from backend.tables import Base, Trade

D = Decimal


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _store(symbol, last_bar, *, base=100.0, n=40):
    """Market store: n-1 flat bars at `base`, then `last_bar` (o,h,l,c)."""
    con = sqlite3.connect(":memory:")
    market_store.ensure_schema(con)
    d0 = date(2024, 1, 1)
    bars = [Bar(d0 + timedelta(days=i), D(str(base)), D(str(base + 1)), D(str(base - 1)),
                D(str(base)), 1000) for i in range(n - 1)]
    o, h, l, c = last_bar
    bars.append(Bar(d0 + timedelta(days=n - 1), D(str(o)), D(str(h)), D(str(l)), D(str(c)), 1000))
    market_store.upsert_bars(con, symbol, bars)
    return con


def _open_trade(db, **kw):
    t = Trade(symbol="AAA", entry_date=date(2024, 1, 1), avg_entry_price=D(100), sl_price=D(95),
              total_qty=35, remaining_qty=35, status="OPEN", **kw)
    db.add(t)
    db.commit()
    return t


def test_eod_exit_closes_on_a_close_below_the_stop(db):
    t = _open_trade(db)                       # stop = 100 - 5 = 95
    con = _store("AAA", (96, 97, 93, 94))     # opens above, closes below 95
    summary = exit_runtime.run_eod_exits(db, con)
    db.refresh(t)
    assert summary["exited"] == 1
    assert t.status == "CLOSED" and t.exit_method == "V2_CLOSE"
    assert t.exit_price < D(95) and t.r_multiple < 0


def test_eod_exit_holds_and_ratchets_and_persists(db):
    t = _open_trade(db)
    con = _store("AAA", (100, 130, 99, 128))  # strong up day, no close below stop
    summary = exit_runtime.run_eod_exits(db, con)
    db.refresh(t)
    assert summary["exited"] == 0 and summary["trailed"] == 1
    assert t.status == "OPEN"
    assert t.highest_high == D(130)           # peak persisted
    assert t.current_stop is not None and Decimal(str(t.current_stop)) >= D(95)  # ratcheted up (or held)


def test_morning_gap_exit_fires_on_gap_below_stop(db):
    t = _open_trade(db)
    con = _store("AAA", (90, 92, 89, 91))     # gaps open below 95
    summary = exit_runtime.run_morning_gap_exits(db, con)
    db.refresh(t)
    assert summary["exited"] == 1
    assert t.status == "CLOSED" and t.exit_method == "V2_GAP" and t.exit_price <= D(90)


def test_morning_gap_check_holds_when_open_above_stop(db):
    t = _open_trade(db)
    con = _store("AAA", (100, 101, 99, 100))  # opens above 95 -> hold
    summary = exit_runtime.run_morning_gap_exits(db, con)
    db.refresh(t)
    assert summary["exited"] == 0 and t.status == "OPEN"


def test_self_heals_trail_from_sl_when_columns_absent(db):
    # a "legacy" trade: current_stop / highest_high never set -> initialise from sl/entry
    t = _open_trade(db)
    assert t.current_stop is None and t.highest_high is None
    con = _store("AAA", (100, 112, 99, 110))  # up day, holds
    exit_runtime.run_eod_exits(db, con)
    db.refresh(t)
    assert t.current_stop is not None and t.highest_high == D(112)
