"""Tests for the live<->runtime bridge (the one seam): scan, projected-volume gate,
live sizing, and the two close-based exit moments. Pure engine + in-memory store."""
import dataclasses
import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from backend.engine import market_store
from backend.engine.kite_data import Bar
from backend.engine.runtime.config import RISK_V2, STRATEGY_V2
from backend.services import strategy_runtime as sr

D = Decimal


def _flat_store(symbol="FLAT", n=200, px=100):
    con = sqlite3.connect(":memory:")
    market_store.ensure_schema(con)
    bars = [Bar(date.fromordinal(date(2023, 1, 2).toordinal() + i), D(px), D(px), D(px), D(px), 1000)
            for i in range(n)]
    market_store.upsert_bars(con, symbol, bars)
    return con


# --- scan delegation -------------------------------------------------------------------

def test_scan_symbol_returns_none_on_flat_series():
    con = _flat_store()
    assert sr.scan_symbol(con, "FLAT") is None            # no contraction/stage -> no signal


def test_scan_symbol_handles_missing_symbol():
    con = _flat_store()
    assert sr.scan_symbol(con, "NOPE") is None            # empty bars -> None, no crash


def test_scan_symbol_as_of_trims_history():
    con = _flat_store()
    # as_of before the first stored bar -> no bars in scope -> None
    assert sr.scan_symbol(con, "FLAT", as_of=date(2000, 1, 1)) is None


def test_scan_universe_collects_only_signals():
    con = _flat_store()
    assert sr.scan_universe(con, ["FLAT", "NOPE"]) == {}   # neither signals


# --- projected breakout-volume gate (decision #1) -------------------------------------

def test_project_full_day_volume_extrapolates_linearly():
    assert sr.project_full_day_volume(100, 75, session_minutes=375) == 500
    assert sr.project_full_day_volume(100, 0) == 0.0       # guard divide-by-zero


def test_breakout_volume_gate_passes_when_projection_clears_2x():
    # 2000 traded with 15 min left -> ~2083 projected >= 2 x 1000
    assert sr.breakout_volume_ok(2000, 360, 1000.0) is True


def test_breakout_volume_gate_fails_when_projection_short():
    # 420 traded near the close -> ~450 projected < 2 x 1000
    assert sr.breakout_volume_ok(420, 350, 1000.0) is False


def test_breakout_volume_gate_disabled_and_missing_sma():
    no_gate = dataclasses.replace(STRATEGY_V2, vol_breakout_k=0.0)
    assert sr.breakout_volume_ok(1, 1, None, params=no_gate) is True
    assert sr.breakout_volume_ok(9_999, 360, None) is False   # gate on, no 50d-avg -> fail safe


# --- live sizing within the portfolio gates -------------------------------------------

def test_live_position_size_normal_and_bear():
    assert sr.live_position_size(D(1_000_000), D(10), True, 3, False) == 350
    assert sr.live_position_size(D(1_000_000), D(10), False, 3, False) == 87   # bear 0.25x


def test_live_position_size_blocked_by_halt_and_cap():
    assert sr.live_position_size(D(1_000_000), D(10), True, 3, True) == 0          # DD halt
    assert sr.live_position_size(D(1_000_000), D(10), True, RISK_V2.max_positions, False) == 0  # cap


# --- composed last-30-min entry --------------------------------------------------------

def test_evaluate_live_entry_happy_path():
    plan = sr.evaluate_live_entry(
        trigger=D(100), stopdist=D(5), last_price=D(101),
        volume_so_far=2000, minutes_elapsed=360, vol_sma50=1000.0,
        equity=D(1_000_000), open_positions=0, halted=False, regime_on=True,
    )
    assert plan is not None
    assert plan.shares == 700 and plan.entry_price == D(101) and plan.stop == D(96)


def test_evaluate_live_entry_blocks_before_trigger_break():
    assert sr.evaluate_live_entry(
        trigger=D(100), stopdist=D(5), last_price=D(99),
        volume_so_far=2000, minutes_elapsed=360, vol_sma50=1000.0,
        equity=D(1_000_000), open_positions=0, halted=False, regime_on=True,
    ) is None


def test_evaluate_live_entry_blocks_on_thin_volume_and_halt():
    base = dict(trigger=D(100), stopdist=D(5), last_price=D(101), equity=D(1_000_000),
                open_positions=0, regime_on=True)
    assert sr.evaluate_live_entry(volume_so_far=420, minutes_elapsed=350, vol_sma50=1000.0,
                                  halted=False, **base) is None    # thin volume
    assert sr.evaluate_live_entry(volume_so_far=2000, minutes_elapsed=360, vol_sma50=1000.0,
                                  halted=True, **base) is None      # drawdown halt


# --- trail open / persist + the two exit moments (decision #2) ------------------------

def test_open_trail_and_rebuild_from_db():
    t = sr.open_trail(D(100), D(5), D(102))
    assert t.stop == D(95) and t.highest_high == D(102) and t.mult == D("5.0")
    rebuilt = sr.trail_from_db(D(100), D(5), current_stop=D(110), highest_high=D(130))
    assert rebuilt.stop == D(110) and rebuilt.highest_high == D(130) and rebuilt.mult == D("5.0")


def test_morning_gap_exit_fires_only_on_gap_below_stop():
    t = sr.open_trail(D(100), D(5), D(100))            # stop = 95
    assert sr.morning_gap_exit(t, D(90)).exited is True   # gaps below -> exit
    assert sr.morning_gap_exit(sr.open_trail(D(100), D(5), D(100)), D(100)) is None  # opens above -> hold


def test_eod_exit_closes_below_stop_or_ratchets():
    t = sr.open_trail(D(100), D(5), D(100))            # stop = 95
    closed = sr.eod_exit(t, Bar(date(2024, 1, 2), D(96), D(97), D(93), D(94), 1000), atr=5.0)
    assert closed.exited and closed.reason == "CLOSE"
    hold = sr.open_trail(D(100), D(5), D(100))
    dec = sr.eod_exit(hold, Bar(date(2024, 1, 2), D(100), D(130), D(99), D(128), 1000), atr=5.0)
    assert not dec.exited and hold.stop == D(105)      # ratcheted to 130 - 5x5
