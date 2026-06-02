"""Tests for the post-close v2 entry job (entry_runtime).

Finds a real breakout in the Kite cache, then asserts run_entries opens a v2 Trade with the
chandelier trail + attribution seeded and a BUY ActionAlert logged; checks the held-symbol
and max-position guards. The flat-series no-entry guard runs without the cache. Cache tests
skip if champion_cache.sqlite is absent (a fresh clone before build_cache_kite)."""
import dataclasses
import os
import sqlite3
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.engine import market_store
from backend.engine.backtest_fast import load_bars
from backend.engine.kite_data import Bar
from backend.engine.precompute import precompute_features
from backend.engine.runtime.config import RISK_V2
from backend.engine.runtime.signal_service import WARMUP, context_from_df, entry_at
from backend.services import entry_runtime
from backend.tables import ActionAlert, Base, Trade

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
needs_cache = pytest.mark.skipif(not os.path.exists(CACHE), reason="champion_cache.sqlite not present")
D = Decimal


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture(scope="module")
def cache_con():
    con = sqlite3.connect(CACHE)
    yield con
    con.close()


def _find_entry(con, *, max_symbols=200):
    """Locate a real (symbol, breakout_date) where the validated v2 entry fires."""
    symbols = [r[0] for r in con.execute("select symbol from done where n>0 order by symbol")]
    for sym in symbols[:max_symbols]:
        bars = load_bars(con, sym)
        if len(bars) < 300:
            continue
        ctx = context_from_df(bars, precompute_features(bars))
        for i in range(len(bars) - 1, max(WARMUP, len(bars) - 400), -1):
            if entry_at(ctx, i) is not None:
                return sym, bars[i].date
    return None, None


@needs_cache
def test_run_entries_opens_a_v2_trade_with_trail(cache_con, db):
    sym, d = _find_entry(cache_con)
    assert sym is not None, "no v2 entry found in the sampled cache symbols"
    # explicit equity so any found name sizes to >=1 share (default 1L can round expensive
    # names to 0 — a real paper-capital consideration, but this test is about trade creation)
    summary = entry_runtime.run_entries(db, cache_con, as_of=d, symbols=[sym],
                                        equity=Decimal("5000000"), cache_path=CACHE)
    assert summary["entered"] == 1
    t = db.query(Trade).filter(Trade.symbol == sym).first()
    assert t is not None and t.status == "OPEN"
    assert t.strategy_version == "v2"
    assert t.signal_type in ("S1B", "S2")
    assert t.total_qty > 0 and t.remaining_qty == t.total_qty
    # the chandelier trail is seeded and the stop sits below entry
    assert t.current_stop is not None and t.highest_high is not None
    assert Decimal(str(t.current_stop)) < Decimal(str(t.avg_entry_price))
    assert t.atr_at_entry is not None and t.avg_trp_at_entry is not None
    # an audit BUY alert was logged, linked to the trade
    a = (db.query(ActionAlert)
         .filter(ActionAlert.symbol == sym, ActionAlert.alert_category == "BUY").first())
    assert a is not None and a.status == "ACTED" and a.resulting_trade_id == t.id


@needs_cache
def test_run_entries_skips_a_symbol_already_held(cache_con, db):
    sym, d = _find_entry(cache_con)
    db.add(Trade(symbol=sym, entry_date=d, avg_entry_price=D(100), total_qty=10,
                 remaining_qty=10, status="OPEN"))
    db.commit()
    summary = entry_runtime.run_entries(db, cache_con, as_of=d, symbols=[sym], cache_path=CACHE)
    assert summary["entered"] == 0


@needs_cache
def test_run_entries_respects_the_max_position_cap(cache_con, db):
    sym, d = _find_entry(cache_con)
    for k in range(RISK_V2.max_positions):          # fill the book to the cap with dummies
        db.add(Trade(symbol=f"DUMMY{k}", entry_date=d, avg_entry_price=D(100),
                     total_qty=1, remaining_qty=1, status="OPEN"))
    db.commit()
    summary = entry_runtime.run_entries(db, cache_con, as_of=d, symbols=[sym], cache_path=CACHE)
    assert summary["entered"] == 0 and summary["blocked"] == 1


def test_run_entries_no_entry_on_a_flat_series(db):
    con = sqlite3.connect(":memory:")
    market_store.ensure_schema(con)
    flat = [Bar(date.fromordinal(date(2023, 1, 2).toordinal() + i), D(100), D(100),
                D(100), D(100), 1000) for i in range(250)]
    market_store.upsert_bars(con, "FLAT", flat)
    summary = entry_runtime.run_entries(db, con, symbols=["FLAT"], cache_path=":memory:")
    assert summary["entered"] == 0
    con.close()
