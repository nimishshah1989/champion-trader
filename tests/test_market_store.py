"""Tests for the Kite market-data ingest — fake adapter + in-memory SQLite, no network."""
import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from backend.engine.backtest_fast import load_bars
from backend.engine.kite_data import Bar
from backend.engine import market_store
from backend.engine.regime import load_regime

NOSLEEP = lambda _s: None   # noqa: E731 — inject to skip real backoff sleeps


def _bar(d, px, vol=1000):
    p = Decimal(str(px))
    return Bar(date.fromisoformat(d), p, p + 1, p - 1, p, vol)


class FakeKite:
    """Canned daily_bars source; records calls; can simulate missing symbols + flakiness."""

    def __init__(self, data, missing=(), flaky_until=0):
        self.data = data
        self.missing = set(missing)
        self.flaky_until = flaky_until      # raise transient errors for the first N calls
        self.calls = []

    def daily_bars(self, symbol, start, end, as_of=None):
        self.calls.append((symbol, start, end, as_of))
        if symbol in self.missing:
            raise KeyError(symbol)
        if len(self.calls) <= self.flaky_until:
            raise ConnectionError("transient")
        eff_end = min(end, as_of) if as_of else end
        return [b for b in self.data.get(symbol, []) if start <= b.date <= eff_end]


def _mem():
    con = sqlite3.connect(":memory:")
    market_store.ensure_schema(con)
    return con


def test_ensure_schema_creates_the_engine_tables():
    con = _mem()
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"bars", "index_bars", "done"} <= tables


def test_ingest_symbol_writes_bars_the_engine_can_read_back():
    con = _mem()
    bars = [_bar("2024-01-01", 100), _bar("2024-01-02", 101), _bar("2024-01-03", 102)]
    src = FakeKite({"AAA": bars})
    n = market_store.ingest_symbol(con, src, "AAA", start=date(2024, 1, 1), end=date(2024, 1, 3), sleep=NOSLEEP)
    assert n == 3
    assert con.execute("select n from done where symbol='AAA'").fetchone()[0] == 3
    read = load_bars(con, "AAA")            # the ACTUAL engine reader
    assert [b.date for b in read] == [b.date for b in bars]
    assert read[0].open == Decimal("100") and read[2].close == Decimal("102")


def test_ingest_symbol_is_incremental_from_the_last_stored_bar():
    con = _mem()
    early = [_bar("2024-01-01", 100), _bar("2024-01-02", 101)]
    src = FakeKite({"AAA": early})
    market_store.ingest_symbol(con, src, "AAA", start=date(2024, 1, 1), end=date(2024, 1, 2), sleep=NOSLEEP)
    # new data arrives; a second run should fetch only AFTER 2024-01-02
    src.data["AAA"] = early + [_bar("2024-01-03", 102), _bar("2024-01-04", 103)]
    src.calls.clear()
    n = market_store.ingest_symbol(con, src, "AAA", start=date(2024, 1, 1), end=date(2024, 1, 4), sleep=NOSLEEP)
    assert n == 2                                    # only the two new bars
    assert src.calls[0][1] == date(2024, 1, 3)       # fetched from the day after the last stored bar
    assert len(load_bars(con, "AAA")) == 4
    assert con.execute("select n from done where symbol='AAA'").fetchone()[0] == 4


def test_reingest_is_idempotent_no_duplicates():
    con = _mem()
    bars = [_bar("2024-01-01", 100), _bar("2024-01-02", 101)]
    src = FakeKite({"AAA": bars})
    market_store.ingest_symbol(con, src, "AAA", start=date(2024, 1, 1), end=date(2024, 1, 2), sleep=NOSLEEP)
    # force a full re-fetch of the same dates via direct upsert -> primary key dedups
    market_store.upsert_bars(con, "AAA", bars)
    assert len(load_bars(con, "AAA")) == 2


def test_ingest_symbol_propagates_not_in_kite():
    con = _mem()
    src = FakeKite({}, missing={"GONE"})
    with pytest.raises(KeyError):
        market_store.ingest_symbol(con, src, "GONE", start=date(2024, 1, 1), end=date(2024, 1, 2), sleep=NOSLEEP)


def test_fetch_history_retries_then_succeeds_on_transient_errors():
    bars = [_bar("2024-01-01", 100)]
    src = FakeKite({"AAA": bars}, flaky_until=2)     # first 2 attempts raise, 3rd succeeds
    out = market_store.fetch_history(src, "AAA", date(2024, 1, 1), date(2024, 1, 1), sleep=NOSLEEP)
    assert [b.date for b in out] == [date(2024, 1, 1)]
    assert len(src.calls) == 3


def test_fetch_history_gives_up_after_max_attempts():
    src = FakeKite({"AAA": []}, flaky_until=99)
    with pytest.raises(ConnectionError):
        market_store.fetch_history(src, "AAA", date(2024, 1, 1), date(2024, 1, 1), sleep=NOSLEEP)


def test_ingest_index_feeds_load_regime(tmp_path):
    db = str(tmp_path / "mkt.db")
    con = sqlite3.connect(db)
    market_store.ensure_schema(con)
    closes = [_bar(f"2024-01-{i:02d}", 1000 + i) for i in range(1, 11)]
    src = FakeKite({"NIFTY 500": closes})
    n = market_store.ingest_index(con, src, "NIFTY 500", start=date(2024, 1, 1), end=date(2024, 1, 10), sleep=NOSLEEP)
    con.close()
    assert n == 10
    regime_on, _ = load_regime(db, "NIFTY 500", sma_window=3, slope_lb=1)
    assert date(2024, 1, 10) in regime_on            # load_regime reads what we ingested
