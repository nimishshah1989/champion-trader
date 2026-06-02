"""Unit tests for the production runtime (config + exit_service + signal_service helpers).

The trade-for-trade equivalence to the validated backtest is covered by
`scripts/run_runtime_parity.py` (the merge gate); these cover the pieces in isolation.
"""
import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from backend.engine.costs import CostModel
from backend.engine.kite_data import Bar
from backend.engine.runtime import exit_service, risk_manager
from backend.engine.runtime.config import (
    RISK_V2,
    STRATEGY_V2,
    RiskParams,
    StrategyParams,
)
from backend.engine.runtime.signal_service import _circuit_locked

D = Decimal

ZERO_COST = CostModel(stt_pct=D(0), exch_txn_pct=D(0), sebi_pct=D(0),
                      stamp_pct_buy=D(0), gst_pct=D(0), dp_per_scrip=D(0))


def _bar(o, h, l, c, v=1_000_000):
    return Bar(date(2024, 1, 2), D(str(o)), D(str(h)), D(str(l)), D(str(c)), v)


@dataclasses.dataclass(frozen=True)
class _Trade:
    symbol: str
    entry_date: date
    exit_date: date
    entry: Decimal
    exit: Decimal
    stopdist: Decimal


# --- config: the single source of validated v2 tunables -------------------------------

def test_strategy_v2_defaults_are_the_validated_thresholds():
    assert STRATEGY_V2.version == "v2"
    assert STRATEGY_V2.min_trp == 2.0
    assert STRATEGY_V2.vol_breakout_k == 2.0
    assert STRATEGY_V2.skip_circuit_locked is True
    assert STRATEGY_V2.chandelier_mult == D("5.0")


def test_risk_v2_defaults_are_the_validated_overlay():
    assert RISK_V2.rpt_pct == 0.35
    assert RISK_V2.max_positions == 15
    assert RISK_V2.bear_frac == D("0.25")
    assert RISK_V2.dd_halt == 0.15
    assert RISK_V2.dd_resume == 0.075
    assert RISK_V2.idle_yield == 0.065
    assert RISK_V2.liquidity_floor_cr == 5.0
    assert RISK_V2.regime_sma_window == 50
    assert RISK_V2.regime_slope_lb == 5


def test_configs_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        STRATEGY_V2.min_trp = 3.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        RISK_V2.rpt_pct = 0.5


def test_slippage_tiers_map_turnover_to_bps():
    s = RISK_V2
    assert s.slippage_for(200.0) == D("0.0010")
    assert s.slippage_for(15.0) == D("0.0010")
    assert s.slippage_for(14.99) == D("0.0025")
    assert s.slippage_for(5.0) == D("0.0025")
    assert s.slippage_for(4.99) == D("0.0050")
    assert s.slippage_for(1.0) == D("0.0050")
    assert s.slippage_for(0.99) == D("0.0100")
    assert s.slippage_for(0.0) == D("0.0100")


def test_replace_builds_a_variant_without_mutating_the_default():
    variant = dataclasses.replace(STRATEGY_V2, vol_breakout_k=3.0, version="v2.1")
    assert variant.vol_breakout_k == 3.0 and variant.version == "v2.1"
    assert STRATEGY_V2.vol_breakout_k == 2.0 and STRATEGY_V2.version == "v2"  # unchanged
    assert isinstance(variant, StrategyParams) and isinstance(RISK_V2, RiskParams)


# --- exit_service: close-based stop + 5xATR chandelier --------------------------------

def test_chandelier_stop_ratchets_up_only():
    assert exit_service.chandelier_stop(D(96), D(120), D(5), D(3)) == D(105)   # raises 96 -> 105
    assert exit_service.chandelier_stop(D(110), D(120), D(5), D(3)) == D(110)  # never lowers


def test_init_trail_opens_at_entry_minus_1r_with_config_mult():
    t = exit_service.init_trail(D(100), D(5), D(102))
    assert t.stop == D(95) and t.highest_high == D(102) and t.mult == D("5.0")
    custom = exit_service.init_trail(D(100), D(5), D(102),
                                     params=dataclasses.replace(STRATEGY_V2, chandelier_mult=D("3.0")))
    assert custom.mult == D("3.0")


def test_step_exits_on_close_below_stop():
    t = exit_service.init_trail(D(100), D(5), D(100))   # stop=95
    dec = exit_service.step(t, _bar(96, 97, 93, 94), atr=5.0)   # opens above stop, closes below
    assert dec.exited and dec.reason == "CLOSE" and dec.fill_price < D(95)


def test_step_exits_on_gap_below_stop():
    t = exit_service.init_trail(D(100), D(5), D(100))   # stop=95
    dec = exit_service.step(t, _bar(90, 92, 89, 91), atr=5.0)   # gaps open below stop
    assert dec.exited and dec.reason == "GAP" and dec.fill_price <= D(90)


def test_step_holds_and_ratchets_the_trail_up():
    t = exit_service.init_trail(D(100), D(5), D(100))   # stop=95
    dec = exit_service.step(t, _bar(100, 130, 99, 128), atr=5.0)
    assert not dec.exited
    assert t.highest_high == D(130)
    assert t.stop == D(105)        # max(95, 130 - 5*5)


def test_step_skips_ratchet_on_nan_atr_but_still_tracks_peak():
    t = exit_service.init_trail(D(100), D(5), D(100))
    dec = exit_service.step(t, _bar(100, 130, 99, 128), atr=float("nan"))
    assert not dec.exited and t.highest_high == D(130) and t.stop == D(95)   # stop unchanged


def test_step_never_lowers_the_stop():
    t = exit_service.init_trail(D(100), D(5), D(100))
    t.stop = D(105)
    exit_service.step(t, _bar(106, 110, 105, 108), atr=5.0)   # 110 - 25 = 85 < 105
    assert t.stop == D(105)


# --- signal_service: the circuit-lock skip (pure helper) ------------------------------

def test_circuit_locked_detects_frozen_bar():
    assert _circuit_locked(D(100), _bar(110, 110, 110, 110)) is True   # high == low


def test_circuit_locked_detects_upper_band_surge_closing_on_high():
    assert _circuit_locked(D(100), _bar(118, 120, 118, 120)) is True   # +20%, close == high


def test_circuit_locked_allows_normal_breakout():
    assert _circuit_locked(D(100), _bar(105, 111, 104, 110)) is False  # +10%, room below high


def test_circuit_locked_guards_nonpositive_prev_close():
    assert _circuit_locked(D(0), _bar(110, 110, 110, 110)) is False


# --- risk_manager: sizing, bear-multiplier, DD breaker, overlay -----------------------

def test_position_size_risks_rpt_pct_over_the_stop_distance():
    # risk 0.35% of Rs10L = Rs3,500 over a Rs10 stop -> 350 shares
    assert risk_manager.position_size(D(1_000_000), D(10), rpt_pct=0.35, bear_mult=D("1.0")) == 350
    # quarter-size in a bear regime -> 875/10 = 87.5 truncates to 87
    assert risk_manager.position_size(D(1_000_000), D(10), rpt_pct=0.35, bear_mult=D("0.25")) == 87


def test_position_size_is_zero_for_nonpositive_stop():
    assert risk_manager.position_size(D(1_000_000), D(0), rpt_pct=0.35, bear_mult=D("1.0")) == 0


def test_bear_multiplier_full_size_in_bull_quarter_in_bear():
    assert risk_manager.bear_multiplier(True) == D("1.0")
    assert risk_manager.bear_multiplier(False) == RISK_V2.bear_frac


def test_update_halt_is_a_15_over_7point5_hysteresis():
    assert risk_manager.update_halt(False, 84.0, 100.0) is True     # -16% -> halt
    assert risk_manager.update_halt(False, 90.0, 100.0) is False    # -10% -> still trading
    assert risk_manager.update_halt(True, 90.0, 100.0) is True      # halted, only -10% recovered -> stay halted
    assert risk_manager.update_halt(True, 95.0, 100.0) is False     # recovered within -7.5% -> resume


def test_simulate_portfolio_books_a_single_winner_cleanly():
    d0, d1, d2, d3, d4 = (date(2024, 1, i) for i in range(1, 6))
    trade = _Trade("AAA", d1, d3, D(100), D(150), D(10))
    params = dataclasses.replace(RISK_V2, idle_yield=0.0)   # no idle drift -> exact arithmetic
    curve = risk_manager.simulate_portfolio(
        [trade], [d0, d1, d2, d3, d4], params=params,
        regime_on={d: True for d in (d0, d1, d2, d3, d4)},
        momentum_score={}, close_on={"AAA": {d1: D(100), d2: D(130), d3: D(150)}},
        start_capital=D(100_000), cost_model=ZERO_COST,
    )
    assert len(curve) == 5
    # 35 shares * (150 - 100) = +1,750 booked at exit; flat thereafter
    assert curve[-1][1] == pytest.approx(101_750.0)
    assert curve[0][1] == pytest.approx(100_000.0)
