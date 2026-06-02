"""Guard tests for the production signal_fn (A5c)."""
from datetime import date, timedelta
from decimal import Decimal

from backend.engine.kite_data import Bar
from backend.engine.production_signal import production_signal


def flat_bars(n, half_range=0.5):
    return [
        Bar(date(2020, 1, 1) + timedelta(days=i),
            Decimal("100"), Decimal(str(100 + half_range)), Decimal(str(100 - half_range)),
            Decimal("100"), 1000)
        for i in range(n)
    ]


def test_insufficient_history_returns_none():
    assert production_signal()(flat_bars(50)) is None


def test_low_trp_is_blocked():
    # 180 bars with ~1% TRP (range 1.0 on price 100) -> below the 2.0 gate -> None
    assert production_signal()(flat_bars(180, half_range=0.5)) is None
