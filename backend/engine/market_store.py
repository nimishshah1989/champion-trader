"""Market-data store + Kite ingest — the data layer that feeds the engine its bars.

The engine reasons on a ``bars`` table (symbol, date, OHLCV) and an ``index_bars`` table
(index_code, date, close); ``backtest_fast.load_bars`` and ``regime.load_regime`` READ
them. This module is the WRITER: it creates that schema and keeps it fresh from Kite's
adjusted history — the SAME feed the backtest used, which closes the price-adjustment gap
that caused the original phantom-loss bug (live == backtest).

Layering: the pure engine/runtime never imports this. The outside world is touched only
through the injectable ``KiteHistoricalAdapter`` (its ``http_get``) and an injectable
``sleep``, so the whole ingest is unit-tested with a fake adapter + in-memory SQLite —
no credentials, no network. The CLI that wires real creds is ``scripts/ingest_kite_daily.py``.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import date, timedelta
from typing import Callable, Optional, Protocol, Sequence

from backend.engine.kite_data import Bar

WINDOW_DAYS = 1800      # < Kite's 2000-day cap for daily candles
THROTTLE_S = 0.35       # ~2.8 req/s, under Kite's 3 req/s historical limit
_RETRY_ATTEMPTS = 5


class BarSource(Protocol):
    """The fetch contract the ingest needs (KiteHistoricalAdapter satisfies it)."""

    def daily_bars(self, symbol: str, start: date, end: date,
                   as_of: Optional[date] = None) -> list[Bar]: ...


def ensure_schema(con: sqlite3.Connection) -> None:
    """Create the bars/index_bars/done tables if absent (matches the proven cache shape)."""
    con.execute("create table if not exists bars(symbol text, date text, open text, high text, "
                "low text, close text, volume integer, delivery_pct real, primary key(symbol,date))")
    con.execute("create table if not exists index_bars(index_code text, date text, close real, "
                "primary key(index_code,date))")
    con.execute("create table if not exists done(symbol text primary key, n integer)")
    con.commit()


def last_bar_date(con: sqlite3.Connection, symbol: str) -> Optional[date]:
    row = con.execute("select max(date) from bars where symbol=?", (symbol,)).fetchone()
    return date.fromisoformat(row[0]) if row and row[0] else None


def last_index_date(con: sqlite3.Connection, index_code: str) -> Optional[date]:
    row = con.execute("select max(date) from index_bars where index_code=?", (index_code,)).fetchone()
    return date.fromisoformat(row[0]) if row and row[0] else None


def upsert_bars(con: sqlite3.Connection, symbol: str, bars: Sequence[Bar]) -> int:
    """Insert-or-replace daily bars (prices stored as Decimal text, exactly as load_bars reads)."""
    con.executemany(
        "insert or replace into bars values(?,?,?,?,?,?,?,?)",
        [(symbol, b.date.isoformat(), str(b.open), str(b.high), str(b.low),
          str(b.close), b.volume, b.delivery_pct) for b in bars],
    )
    return len(bars)


def upsert_index(con: sqlite3.Connection, index_code: str, bars: Sequence[Bar]) -> int:
    con.executemany(
        "insert or replace into index_bars values(?,?,?)",
        [(index_code, b.date.isoformat(), float(b.close)) for b in bars],
    )
    return len(bars)


def fetch_history(source: BarSource, symbol: str, start: date, end: date, *,
                  as_of: Optional[date] = None, throttle: float = THROTTLE_S,
                  sleep: Callable[[float], None] = time.sleep) -> list[Bar]:
    """Full daily history across <=1800-day windows, deduped by date, leakage-safe.

    Retries each window up to 4 times with exponential backoff on transient (network/429)
    errors; a KeyError (symbol absent from Kite) is not transient and propagates.
    """
    by_date: dict[date, Bar] = {}
    a = start
    while a <= end:
        b = min(a + timedelta(days=WINDOW_DAYS), end)
        for bar in _fetch_window(source, symbol, a, b, as_of, sleep):
            by_date[bar.date] = bar
        if throttle:
            sleep(throttle)
        a = b + timedelta(days=1)
    return [by_date[d] for d in sorted(by_date)]


def _fetch_window(source: BarSource, symbol: str, a: date, b: date,
                  as_of: Optional[date], sleep: Callable[[float], None]) -> list[Bar]:
    delay = 2.0
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            return source.daily_bars(symbol, a, b, as_of=as_of)
        except KeyError:
            raise                                   # symbol not in Kite -> not transient
        except Exception:
            if attempt == _RETRY_ATTEMPTS - 1:
                raise
            sleep(delay)
            delay *= 2
    return []


def ingest_symbol(con: sqlite3.Connection, source: BarSource, symbol: str, *,
                  start: date, end: date, as_of: Optional[date] = None,
                  throttle: float = THROTTLE_S, sleep: Callable[[float], None] = time.sleep) -> int:
    """Incrementally fetch+store one symbol from the day after its last stored bar.

    Returns the number of new bars written. Updates ``done.n`` to the symbol's total.
    """
    last = last_bar_date(con, symbol)
    frm = (last + timedelta(days=1)) if last else start
    n = 0
    if frm <= end:
        bars = fetch_history(source, symbol, frm, end, as_of=as_of, throttle=throttle, sleep=sleep)
        n = upsert_bars(con, symbol, bars)
    total = con.execute("select count(*) from bars where symbol=?", (symbol,)).fetchone()[0]
    con.execute("insert or replace into done values(?,?)", (symbol, total))
    con.commit()
    return n


def ingest_index(con: sqlite3.Connection, source: BarSource, index_code: str, *,
                 start: date, end: date, as_of: Optional[date] = None,
                 throttle: float = THROTTLE_S, sleep: Callable[[float], None] = time.sleep) -> int:
    """Incrementally fetch+store an index's daily closes into index_bars."""
    last = last_index_date(con, index_code)
    frm = (last + timedelta(days=1)) if last else start
    if frm > end:
        return 0
    bars = fetch_history(source, index_code, frm, end, as_of=as_of, throttle=throttle, sleep=sleep)
    n = upsert_index(con, index_code, bars)
    con.commit()
    return n
