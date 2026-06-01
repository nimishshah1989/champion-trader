"""Tests for the chandelier trailing-stop ratchet (R-3 ride-winners exit)."""
from decimal import Decimal

from backend.engine.backtest_fast import _chandelier_stop


def D(x):
    return Decimal(str(x))


def test_chandelier_ratchets_up():
    # HH 120, ATR 5, mult 3 -> trail 105; above the prior stop 96 -> moves up to 105
    assert _chandelier_stop(D(96), D(120), D(5), D(3)) == D(105)


def test_chandelier_never_moves_down():
    # trail would be 105 (120 - 15) but prior stop is 110 -> stays 110
    assert _chandelier_stop(D(110), D(120), D(5), D(3)) == D(110)
