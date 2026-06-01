"""Golden + property tests for the NSE cost & capital-gains tax model (A1).

Written BEFORE the implementation (TDD). The golden values are derived by hand
from the default FY2025-26 delivery rates in backend/engine/costs.py and must be
reconciled against a real Zerodha contract note before go-live.
"""
from decimal import Decimal

from backend.engine.costs import (
    CostModel,
    capital_gains_tax,
    STCG_RATE,
    LTCG_RATE,
    LTCG_EXEMPTION,
)


def D(x) -> Decimal:
    return Decimal(str(x))


# --- Trading-cost golden cases (hand-computed) ---------------------------------

def test_buy_costs_one_lakh_golden():
    # Buy ₹1,00,000 delivery:
    #   STT 0.1%=100, exch 0.00297%=2.97, SEBI 0.0001%=0.10, stamp 0.015%=15,
    #   brokerage 0, GST 18% of (0+2.97+0.10)=0.5526  ->  118.62
    assert CostModel().buy_costs(D(100000)) == D("118.62")


def test_sell_costs_one_scrip_golden():
    # Sell ₹1,10,000, 1 scrip:
    #   STT 0.1%=110, exch 0.00297%=3.267, SEBI 0.0001%=0.11, stamp 0,
    #   DP 13.5, GST 18% of (0+3.267+0.11+13.5)=3.03786  ->  129.91
    assert CostModel().sell_costs(D(110000), scrips=1) == D("129.91")


def test_round_trip_is_buy_plus_sell():
    m = CostModel()
    assert m.round_trip_costs(D(100000), D(110000), scrips=1) == (
        m.buy_costs(D(100000)) + m.sell_costs(D(110000), scrips=1)
    )


# --- Property: the flat DP fee dominates small tickets (the council's point) ----

def test_dp_fee_dominates_small_tickets():
    m = CostModel()
    small_pct = m.sell_costs(D(4000)) / D(4000)
    large_pct = m.sell_costs(D(100000)) / D(100000)
    assert small_pct > large_pct                     # flat fee hurts small tickets more
    assert small_pct > D("0.004")                    # >0.4% of a ₹4,000 ticket


def test_costs_monotonic_in_value():
    m = CostModel()
    assert m.buy_costs(D(50000)) < m.buy_costs(D(100000)) < m.buy_costs(D(200000))


# --- Capital-gains tax golden cases --------------------------------------------

def test_stcg_taxed_at_20pct():
    assert capital_gains_tax(net_stcg=D(50000), net_ltcg=D(0)) == D("10000.00")


def test_ltcg_taxed_above_exemption():
    # (200000 - 125000) * 12.5% = 9375
    assert capital_gains_tax(net_stcg=D(0), net_ltcg=D(200000)) == D("9375.00")


def test_ltcg_below_exemption_is_zero():
    assert capital_gains_tax(net_stcg=D(0), net_ltcg=D(100000)) == D("0.00")


def test_losses_are_not_taxed():
    assert capital_gains_tax(net_stcg=D(-5000), net_ltcg=D(-20000)) == D("0.00")


def test_current_rates():
    assert STCG_RATE == Decimal("0.20")
    assert LTCG_RATE == Decimal("0.125")
    assert LTCG_EXEMPTION == Decimal("125000")
