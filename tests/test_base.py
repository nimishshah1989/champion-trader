"""Golden tests for base-structure analysis (A3d)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.engine.kite_data import Bar
from backend.engine.base import analyze_base


def bar(i, h, l, c) -> Bar:
    return Bar(
        date(2020, 1, 1) + timedelta(days=i),
        Decimal(str(c)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)), 1000,
    )


def _advance_then(consolidation_bars):
    """30-bar advance 80->100, then the given consolidation bars."""
    bars = [bar(i, 80 + (20 / 29) * i, 80 + (20 / 29) * i, 80 + (20 / 29) * i) for i in range(30)]
    return bars + consolidation_bars


def test_valid_base():
    # 25 bars consolidating below 100 with a 10% pullback (low 90), after a 25% advance.
    bars = _advance_then([bar(30 + j, 98, 90, 94) for j in range(25)])
    r = analyze_base(bars)
    assert r.is_valid_base is True
    assert r.base_bars == 25
    assert r.depth_pct == pytest.approx(10.0, abs=0.5)
    assert r.prior_advance_pct == pytest.approx(25.0, abs=1.0)


def test_too_deep_base_rejected():
    bars = _advance_then([bar(30 + j, 98, 40, 70) for j in range(25)])   # 60% deep
    r = analyze_base(bars)
    assert r.depth_pct > 35.0
    assert r.is_valid_base is False


def test_no_prior_advance_rejected():
    # flat (no advance) then a normal consolidation
    bars = [bar(i, 100, 100, 100) for i in range(30)] + [bar(30 + j, 98, 90, 94) for j in range(25)]
    r = analyze_base(bars)
    assert r.prior_advance_pct < 20.0
    assert r.is_valid_base is False


def test_too_short_base_rejected():
    bars = _advance_then([bar(30 + j, 98, 90, 94) for j in range(10)])   # only 10 bars basing
    r = analyze_base(bars)
    assert r.base_bars == 10
    assert r.is_valid_base is False


def test_insufficient_bars():
    r = analyze_base([bar(i, 100, 99, 100) for i in range(10)])
    assert r.is_valid_base is False
    assert r.base_bars == 0
