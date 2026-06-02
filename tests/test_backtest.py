"""Tests for the event-driven backtest loop (A5b), with an injected signal."""
from datetime import date, timedelta
from decimal import Decimal

from backend.engine.backtest import run_backtest
from backend.engine.costs import CostModel
from backend.engine.kite_data import Bar

ZERO_COST = CostModel(
    brokerage_pct=Decimal(0), stt_pct=Decimal(0), exch_txn_pct=Decimal(0),
    sebi_pct=Decimal(0), stamp_pct_buy=Decimal(0), gst_pct=Decimal(0), dp_per_scrip=Decimal(0),
)


def bar(i, o, h, l, c):
    return Bar(date(2020, 1, 1) + timedelta(days=i),
               Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)), 1000)


# arms a single setup (trigger 101, stop-distance 5) on the first closed bar
def _signal(history):
    return (Decimal("101"), Decimal("5")) if len(history) == 1 else None


_TARGET_DATA = {"X": [bar(0, 100, 100, 100, 100), bar(1, 100, 102, 99, 101),
                      bar(2, 105, 108, 103, 107), bar(3, 110, 112, 109, 111)]}

_STOP_DATA = {"X": [bar(0, 100, 100, 100, 100), bar(1, 100, 102, 99, 101),
                    bar(2, 95, 97, 94, 96)]}


def test_target_win_zero_cost():
    r = run_backtest(_TARGET_DATA, _signal, starting_capital=Decimal("100000"),
                     rpt_pct=0.5, target_r=2.0, slippage=Decimal(0), cost_model=ZERO_COST)
    assert r.num_trades == 1
    assert r.r_multiples[0] == 2.0                      # +2R exactly, no costs/slippage
    assert r.final_equity == 101000.0                   # 100 shares * (111-101) = +1000


def test_gap_through_stop_loses_more_than_1R():
    # bar2 OPENS at 95, below the 96 stop -> honest fill at the gap-open, not the stop.
    r = run_backtest(_STOP_DATA, _signal, starting_capital=Decimal("100000"),
                     rpt_pct=0.5, target_r=2.0, slippage=Decimal(0), cost_model=ZERO_COST)
    assert r.num_trades == 1
    assert r.r_multiples[0] == -1.2                     # (95-101)/5 -> worse than -1R
    assert r.final_equity == 99400.0


def test_costs_and_slippage_haircut_the_edge():
    r = run_backtest(_TARGET_DATA, _signal, starting_capital=Decimal("100000"),
                     rpt_pct=0.5, target_r=2.0)          # default real costs + 10bps slippage
    assert r.num_trades == 1
    assert 1.8 < r.r_multiples[0] < 1.98                # a clean +2R is eroded by friction
    assert 100000.0 < r.final_equity < 101000.0
