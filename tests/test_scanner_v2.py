"""Tests for the v2 SETUP scanner (scanner_engine.run_v2_scan) — reads the Kite bars store.

Uses the real champion_cache.sqlite to locate a genuine v2 setup (deterministic), then
asserts the scanner surfaces it in a ScanResult-persistable shape. Skips if the cache is
absent (e.g. a fresh clone before build_cache_kite)."""
import dataclasses
import os
import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from backend.engine.backtest_fast import load_bars
from backend.engine.kite_data import Bar
from backend.engine import market_store
from backend.engine.precompute import precompute_features
from backend.engine.runtime.config import RISK_V2, STRATEGY_V2
from backend.engine.runtime.signal_service import WARMUP, context_from_df, setup_at
from backend.services import scanner_engine
from backend.tables import ScanResult

CACHE = "/home/user/champion-trader/champion_cache.sqlite"
SCAN_COLS = {c.name for c in ScanResult.__table__.columns}
pytestmark = pytest.mark.skipif(not os.path.exists(CACHE), reason="champion_cache.sqlite not present")


def _find_setup(con, *, floor_cr, max_symbols=150):
    """Locate a real (symbol, signal_date) with a v2 setup on a >= floor name."""
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


@pytest.fixture(scope="module")
def cache_con():
    con = sqlite3.connect(CACHE)
    yield con
    con.close()


def test_run_v2_scan_surfaces_a_real_setup(cache_con):
    sym, sig_date = _find_setup(cache_con, floor_cr=RISK_V2.liquidity_floor_cr)
    assert sym is not None, "no v2 setup found in the sampled cache symbols"
    rows = scanner_engine.run_v2_scan(cache_con, [sym], sig_date, as_of=sig_date)
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == sym
    assert row["scan_type"] == "V2"
    assert row["watchlist_bucket"] == "READY"
    assert row["stage"] in ("S1B", "S2")
    assert row["trigger_level"] > 0 and isinstance(row["trigger_level"], Decimal)
    assert row["passes_liquidity_filter"] is True
    assert row["has_min_20_bar_base"] is True


def test_run_v2_scan_rows_are_scanresult_persistable(cache_con):
    sym, sig_date = _find_setup(cache_con, floor_cr=RISK_V2.liquidity_floor_cr)
    rows = scanner_engine.run_v2_scan(cache_con, [sym], sig_date, as_of=sig_date)
    for row in rows:
        assert set(row).issubset(SCAN_COLS), f"non-column keys: {set(row) - SCAN_COLS}"
        ScanResult(**row)   # must construct without error (the persist path is ScanResult(**dict))


def test_run_v2_scan_respects_the_liquidity_floor(cache_con):
    sym, sig_date = _find_setup(cache_con, floor_cr=RISK_V2.liquidity_floor_cr)
    huge_floor = dataclasses.replace(RISK_V2, liquidity_floor_cr=1e12)   # nothing is this liquid
    assert scanner_engine.run_v2_scan(cache_con, [sym], sig_date, as_of=sig_date, risk=huge_floor) == []


def test_run_v2_scan_empty_on_flat_series():
    con = sqlite3.connect(":memory:")
    market_store.ensure_schema(con)
    flat = [Bar(date.fromordinal(date(2023, 1, 2).toordinal() + i), Decimal(100), Decimal(100),
                Decimal(100), Decimal(100), 1000) for i in range(250)]
    market_store.upsert_bars(con, "FLAT", flat)
    assert scanner_engine.run_v2_scan(con, ["FLAT"], "2023-09-01") == []
    con.close()
