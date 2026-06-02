"""Tests for the Weinstein stage classifier (A3b), incl. the topping-bug fix."""
from datetime import date, timedelta
from decimal import Decimal

from backend.engine.kite_data import Bar
from backend.engine.stage import UNKNOWN, _stage_from_signals, classify_stage


def mkbars(closes):
    out = []
    for i, c in enumerate(closes):
        cd = Decimal(str(c))
        out.append(Bar(date(2020, 1, 1) + timedelta(days=i), cd, cd, cd, cd, 1000))
    return out


# --- pure decision function: full, mutually-exclusive coverage ---

def test_rising_ma_above_with_higher_highs_is_S2():
    assert _stage_from_signals(2.0, 1.0, True) == "S2"


def test_rising_ma_above_without_higher_highs_is_S1B():
    assert _stage_from_signals(2.0, 1.0, False) == "S1B"


def test_rising_ma_price_below_is_S1B():
    assert _stage_from_signals(-2.0, 1.0, True) == "S1B"


def test_s1b_demoted_to_s1_without_breakout_volume():
    assert _stage_from_signals(2.0, 1.0, False, breakout_volume_confirmed=False) == "S1"


def test_falling_ma_price_below_is_S4():
    assert _stage_from_signals(-3.0, -1.0, True) == "S4"


def test_topping_above_rolling_over_ma_is_S3_not_buy():
    # THE BUG FIX: price above a FALLING MA must be S3 (topping), never S1B/S2.
    assert _stage_from_signals(2.0, -1.0, True) == "S3"


def test_flat_ma_is_S1():
    assert _stage_from_signals(2.0, 0.2, True) == "S1"
    assert _stage_from_signals(-1.0, -0.3, False) == "S1"


# --- integration on synthetic series ---

def test_uptrend_classifies_S2():
    assert classify_stage(mkbars([100 + 0.5 * i for i in range(200)])) == "S2"


def test_downtrend_classifies_S4():
    assert classify_stage(mkbars([200 - 0.5 * i for i in range(200)])) == "S4"


def test_flat_classifies_S1():
    assert classify_stage(mkbars([100.0] * 200)) == "S1"


def test_insufficient_bars_is_unknown():
    assert classify_stage(mkbars([100.0] * 50)) == UNKNOWN
