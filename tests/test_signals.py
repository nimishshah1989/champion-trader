"""Tests for PPC/NPC detection + watchlist-state assembly (A3e)."""
from datetime import date, timedelta
from decimal import Decimal

from backend.engine.kite_data import Bar
from backend.engine.metrics import CandleFeatures
from backend.engine.signals import (
    AWAY,
    NEAR,
    READY,
    _bucket,
    classify_watch_state,
    detect_npc_candle,
    detect_ppc_candle,
)


def feat(trp_ratio, close_position, volume_ratio, is_green):
    return CandleFeatures(
        trp=0.0, avg_trp=0.0, trp_ratio=trp_ratio, trp_z=0.0,
        close_position=close_position, volume_ratio=volume_ratio, volume_z=0.0,
        is_green=is_green,
    )


def bar(i, c):
    cd = Decimal(str(c))
    return Bar(date(2020, 1, 1) + timedelta(days=i), cd, cd, cd, cd, 1000)


# --- PPC / NPC candle detection ---

def test_ppc_candle_pass():
    assert detect_ppc_candle(feat(2.0, 0.7, 1.8, True)) is True


def test_ppc_candle_fails_on_red_or_weak():
    assert detect_ppc_candle(feat(2.0, 0.7, 1.8, False)) is False   # red candle
    assert detect_ppc_candle(feat(2.0, 0.5, 1.8, True)) is False    # close too low in range
    assert detect_ppc_candle(feat(2.0, 0.7, 1.0, True)) is False    # volume too low


def test_npc_candle_pass():
    assert detect_npc_candle(feat(2.0, 0.2, 1.8, False)) is True


def test_npc_candle_fails_when_green():
    assert detect_npc_candle(feat(2.0, 0.2, 1.8, True)) is False


# --- bucket partition: READY = contraction + trigger ---

def test_bucket_ready_requires_contraction():
    assert _bucket(True, True, True, True, True) == READY
    assert _bucket(True, True, False, True, True) == NEAR     # base but no contraction
    assert _bucket(True, False, False, True, True) == AWAY    # no base


def test_bucket_hard_gates():
    assert _bucket(False, True, True, True, True) == AWAY     # weak stage
    assert _bucket(True, True, True, False, True) == AWAY     # weak RS
    assert _bucket(True, True, True, True, False) == AWAY     # weak sector


# --- integration ---

def test_weak_rs_forces_away_even_in_uptrend():
    bars = [bar(i, 80 + (20 / 199) * i) for i in range(200)]   # uptrend -> S2
    ws = classify_watch_state(bars, rs_percentile=10.0)
    assert ws.stage_ok is True
    assert ws.rs_ok is False
    assert ws.bucket == AWAY


def test_pure_uptrend_is_not_a_base():
    bars = [bar(i, 80 + (20 / 199) * i) for i in range(200)]
    ws = classify_watch_state(bars, rs_percentile=90.0, sector_strong=True)
    assert ws.stage_ok is True
    assert ws.base_ok is False          # a runaway ramp is not a base
    assert ws.bucket == AWAY
