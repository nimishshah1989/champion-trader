"""Tests for the contraction detector (A3c), incl. the inverted-tolerance fix."""
from datetime import date, timedelta
from decimal import Decimal

from backend.engine.kite_data import Bar
from backend.engine.contraction import (
    _consecutive_narrowing,
    _linreg_slope,
    detect_contraction,
)


def bar(i, h, l, c) -> Bar:
    return Bar(
        date(2020, 1, 1) + timedelta(days=i),
        Decimal(str(c)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)), 1000,
    )


# --- pure helpers (exact goldens) ---

def test_consecutive_narrowing_strict():
    assert _consecutive_narrowing([5, 4, 3, 2]) == 3
    assert _consecutive_narrowing([3, 3, 3]) == 2          # equal = not-widening
    assert _consecutive_narrowing([2, 3, 4, 5]) == 0       # expanding
    assert _consecutive_narrowing([5, 4, 6]) == 0          # BUG FIX: a wider bar breaks it


def test_linreg_slope_sign():
    assert _linreg_slope([5, 4, 3, 2, 1]) < 0
    assert _linreg_slope([1, 2, 3, 4, 5]) > 0
    assert abs(_linreg_slope([3, 3, 3, 3])) < 1e-9


# --- integration ---

def _coiling_series():
    bars = [bar(i, 105, 95, 100) for i in range(25)]       # wide bars, resistance high = 105
    for j in range(15):                                    # progressively narrowing, coiling at the top
        rng = 4 - 0.25 * j                                 # 4.0 -> 0.5, strictly shrinking
        hi, lo, cl = 103 + rng / 2, 103 - rng / 2, 103 + rng / 2 - 0.05
        bars.append(bar(25 + j, hi, lo, cl))
    return bars


def test_detects_contraction():
    r = detect_contraction(_coiling_series())
    assert r.narrowing_count >= 3
    assert r.near_resistance is True
    assert r.atr_slope_pct < 0
    assert r.atr_percentile <= 0.35          # current ATR is compressed vs its own range
    assert r.is_contraction is True
    assert r.trigger_level > Decimal("100")


def test_no_contraction_when_volatility_elevated():
    # long quiet region, then a recent volatility blow-up: current ATR sits HIGH
    # in its own range -> not compressed -> not a contraction.
    bars = [bar(i, 100.5, 99.5, 100) for i in range(40)]   # quiet, range 1
    for j in range(12):
        bars.append(bar(40 + j, 108, 92, 100))             # recent blow-up, range 16
    r = detect_contraction(bars)
    assert r.atr_percentile > 0.35
    assert r.is_contraction is False


def test_no_contraction_when_far_from_resistance():
    bars = [bar(i, 105, 95, 100) for i in range(25)]
    for j in range(15):
        rng = 4 - 0.25 * j
        bars.append(bar(25 + j, 80 + rng / 2, 80 - rng / 2, 80))   # coiling far below the 105 high
    r = detect_contraction(bars)
    assert r.near_resistance is False
    assert r.is_contraction is False
