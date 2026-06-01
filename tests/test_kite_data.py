"""Unit tests for the Kite historical data adapter (A2).

All offline — a fake transport returns canned Kite responses, so the suite runs
with no network and no live token. The critical property is the LEAKAGE GUARD:
given an ``as_of`` date, the adapter must never request or return any bar after it.
"""
import json
from datetime import date
from decimal import Decimal

import pytest

from backend.engine.kite_data import Bar, KiteHistoricalAdapter

CANDLES = [
    ["2026-04-20T00:00:00+0530", 100, 105, 99, 104, 1000],
    ["2026-04-21T00:00:00+0530", 104, 108, 103, 107, 1200],
    ["2026-04-22T00:00:00+0530", 107, 110, 106, 109, 1500],
    ["2026-04-23T00:00:00+0530", 109, 112, 108, 111, 1300],
]


class FakeTransport:
    """Captures requested URLs and returns canned Kite payloads.

    Simulates Kite by only returning candles whose date is <= the request's
    ``to`` parameter — so the test can prove the adapter caps ``to`` at as_of.
    """

    def __init__(self, candles=CANDLES):
        self.calls: list[str] = []
        self._candles = candles

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        if "/instruments/NSE" in url:
            return b"instrument_token,tradingsymbol\n738561,RELIANCE\n5633,INFY\n"
        if "/instruments/historical/" in url:
            to = url.split("to=")[1].split("&")[0]
            sel = [c for c in self._candles if c[0][:10] <= to]
            return json.dumps({"data": {"candles": sel}}).encode()
        raise AssertionError(f"unexpected url: {url}")


def _adapter(candles=CANDLES):
    ft = FakeTransport(candles)
    return KiteHistoricalAdapter("key", "token", http_get=ft), ft


def test_instrument_token_lookup():
    a, _ = _adapter()
    assert a.instrument_token("RELIANCE") == 738561
    assert a.instrument_token("INFY") == 5633


def test_unknown_symbol_raises():
    a, _ = _adapter()
    with pytest.raises(KeyError):
        a.instrument_token("NOPE")


def test_instruments_loaded_once():
    a, ft = _adapter()
    a.instrument_token("RELIANCE")
    a.instrument_token("INFY")
    assert sum(1 for u in ft.calls if "/instruments/NSE" in u) == 1


def test_daily_bars_parses_to_decimal():
    a, _ = _adapter()
    bars = a.daily_bars("RELIANCE", date(2026, 4, 20), date(2026, 4, 23))
    assert len(bars) == 4
    assert bars[0] == Bar(date(2026, 4, 20), Decimal("100"), Decimal("105"), Decimal("99"), Decimal("104"), 1000)
    assert all(isinstance(b.close, Decimal) for b in bars)


def test_leakage_guard_caps_to_at_as_of():
    a, ft = _adapter()
    bars = a.daily_bars("RELIANCE", date(2026, 4, 20), date(2026, 4, 23), as_of=date(2026, 4, 21))
    hist_url = next(u for u in ft.calls if "historical" in u)
    assert "to=2026-04-21" in hist_url            # never even requests future data
    assert all(b.date <= date(2026, 4, 21) for b in bars)
    assert len(bars) == 2


def test_no_request_when_start_after_as_of():
    a, ft = _adapter()
    bars = a.daily_bars("RELIANCE", date(2026, 4, 22), date(2026, 4, 23), as_of=date(2026, 4, 20))
    assert bars == []
    assert not any("historical" in u for u in ft.calls)   # no future fetch at all
