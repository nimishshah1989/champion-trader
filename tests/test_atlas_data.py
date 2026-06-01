"""Offline tests for the Atlas REST OHLCV adapter (A2b): pagination + leakage."""
import json
import urllib.parse
from datetime import date, timedelta

from backend.engine.atlas_data import AtlasOHLCVAdapter


def _rows(n):
    base = date(2010, 1, 1)
    rows = [
        {"date": (base + timedelta(days=i)).isoformat(), "open": 100, "high": 101,
         "low": 99, "close": 100, "volume": 1000, "delivery_pct": 50.0}
        for i in range(n)
    ]
    rows[0]["delivery_pct"] = None       # exercise the None path
    return rows


class FakeREST:
    def __init__(self, n=2500):
        self.rows = _rows(n)
        self.instrument_calls = 0

    def __call__(self, url, headers):
        if "/de_instrument" in url:
            self.instrument_calls += 1
            return json.dumps([{"id": "IID-RELIANCE"}]).encode()
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        off = int(q.get("offset", ["0"])[0])
        lim = int(q.get("limit", ["1000"])[0])
        return json.dumps(self.rows[off:off + lim]).encode()


def _adapter(n=2500):
    f = FakeREST(n)
    return AtlasOHLCVAdapter("http://x", "key", http_get=f), f


def test_paginates_across_pages():
    a, _ = _adapter(2500)
    bars = a.daily_bars("RELIANCE", date(2010, 1, 1), date(2099, 1, 1))
    assert len(bars) == 2500                       # 1000 + 1000 + 500


def test_delivery_pct_parsed_incl_none():
    a, _ = _adapter(10)
    bars = a.daily_bars("RELIANCE", date(2010, 1, 1), date(2099, 1, 1))
    assert bars[0].delivery_pct is None
    assert bars[1].delivery_pct == 50.0


def test_leakage_guard_drops_future():
    a, _ = _adapter(2500)
    cutoff = date(2010, 1, 1) + timedelta(days=100)
    bars = a.daily_bars("RELIANCE", date(2010, 1, 1), date(2099, 1, 1), as_of=cutoff)
    assert all(b.date <= cutoff for b in bars)
    assert len(bars) == 101                        # days 0..100 inclusive


def test_instrument_id_cached():
    a, f = _adapter(10)
    a.daily_bars("RELIANCE", date(2010, 1, 1), date(2099, 1, 1))
    a.daily_bars("RELIANCE", date(2010, 1, 1), date(2099, 1, 1))
    assert f.instrument_calls == 1
