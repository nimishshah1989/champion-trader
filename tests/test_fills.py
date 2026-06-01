"""Golden tests for the honest fill engine (A4). Slippage = 10 bps."""
from decimal import Decimal

from backend.engine.fills import Fill, fill_entry, fill_stop, fill_target, resolve_open_bar


def D(x) -> Decimal:
    return Decimal(str(x))


def test_entry_not_triggered():
    assert fill_entry(D(100), D(99), D(99.5)) is None        # high < trigger


def test_entry_intraday_break():
    assert fill_entry(D(100), D(99), D(101)) == D("100.10")  # 100 * 1.001


def test_entry_gap_up_pays_the_open():
    assert fill_entry(D(100), D(103), D(104)) == D("103.10")  # not the trigger — the higher open


def test_stop_not_hit():
    assert fill_stop(D(95), D(98), D(96)) is None


def test_stop_intraday():
    assert fill_stop(D(95), D(98), D(94)) == D("94.91")      # 95 * 0.999 = 94.905 -> 94.91


def test_stop_gap_down_fills_below_the_stop():
    # THE honest case: a gap-down opens below the stop -> you fill at the open, worse.
    assert fill_stop(D(95), D(90), D(88)) == D("89.91")      # 90 * 0.999


def test_target_hit():
    assert fill_target(D(120), D(100), D(121)) == D("119.88")  # 120 * 0.999


def test_resolve_stop_wins_same_bar():
    f = resolve_open_bar(D(100), D(121), D(88), stop=D(95), target=D(120))
    assert f == Fill(D("94.91"), "STOP")                     # touched both -> stop wins


def test_resolve_target_only():
    f = resolve_open_bar(D(100), D(121), D(96), stop=D(95), target=D(120))
    assert f == Fill(D("119.88"), "TARGET")


def test_resolve_neither():
    assert resolve_open_bar(D(100), D(110), D(96), stop=D(95), target=D(120)) is None
