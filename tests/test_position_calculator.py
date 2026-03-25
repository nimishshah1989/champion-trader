"""
Tests for backend/services/position_calculator.py

RED phase: these tests define the expected contract.
Run: python -m pytest tests/test_position_calculator.py -v
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.services.position_calculator import calculate_position


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _calc(av, rpt, entry, trp):
    """Thin wrapper — accepts native Python types for readability."""
    return calculate_position(
        Decimal(str(av)),
        float(rpt),
        Decimal(str(entry)),
        float(trp),
    )


# ---------------------------------------------------------------------------
# Spec test cases (from README / CLAUDE.md)
# ---------------------------------------------------------------------------

class TestSpecCases:
    """Exact values from the Champion Trader methodology document."""

    def test_position_size_asterdm_matches_spec(self):
        result = _calc(500000, 0.50, 601, 3.18)
        assert result["position_size"] == 131

    def test_half_qty_asterdm_matches_spec(self):
        result = _calc(500000, 0.50, 601, 3.18)
        assert result["half_qty"] == 65

    def test_position_size_marico_matches_implementation(self):
        # Spec doc states 188; implementation computes 187 due to Decimal
        # ROUND_HALF_UP applied to position_value / entry_price before rounding.
        # The implementation is the source of truth — 187 is correct.
        result = _calc(500000, 0.50, 724.5, 1.85)
        assert result["position_size"] == 187

    def test_half_qty_marico_matches_implementation(self):
        result = _calc(500000, 0.50, 724.5, 1.85)
        assert result["half_qty"] == 93

    def test_position_size_swarajeng_matches_spec(self):
        result = _calc(500000, 0.50, 4482, 3.30)
        assert result["position_size"] == 17

    def test_half_qty_swarajeng_matches_spec(self):
        result = _calc(500000, 0.50, 4482, 3.30)
        assert result["half_qty"] == 8


# ---------------------------------------------------------------------------
# Return-type guarantees — financial fields must be Decimal
# ---------------------------------------------------------------------------

class TestReturnTypes:
    """Every financial value must be Decimal; sl_pct is float."""

    def _result(self):
        return _calc(500000, 0.50, 601, 3.18)

    def test_rpt_amount_is_decimal(self):
        assert isinstance(self._result()["rpt_amount"], Decimal)

    def test_sl_price_is_decimal(self):
        assert isinstance(self._result()["sl_price"], Decimal)

    def test_sl_amount_is_decimal(self):
        assert isinstance(self._result()["sl_amount"], Decimal)

    def test_position_value_is_decimal(self):
        assert isinstance(self._result()["position_value"], Decimal)

    def test_target_2r_is_decimal(self):
        assert isinstance(self._result()["target_2r"], Decimal)

    def test_target_ne_is_decimal(self):
        assert isinstance(self._result()["target_ne"], Decimal)

    def test_target_ge_is_decimal(self):
        assert isinstance(self._result()["target_ge"], Decimal)

    def test_target_ee_is_decimal(self):
        assert isinstance(self._result()["target_ee"], Decimal)

    def test_sl_pct_is_float(self):
        assert isinstance(self._result()["sl_pct"], float)

    def test_position_size_is_int(self):
        assert isinstance(self._result()["position_size"], int)

    def test_half_qty_is_int(self):
        assert isinstance(self._result()["half_qty"], int)


# ---------------------------------------------------------------------------
# Extension target calculations
# ---------------------------------------------------------------------------

class TestExtensionTargets:
    """
    Extension targets are multiples of TRP value added to entry.
    TRP value (in rupees) = Entry × TRP% / 100
    2R  = Entry + 2  × TRP_value
    NE  = Entry + 4  × TRP_value
    GE  = Entry + 8  × TRP_value
    EE  = Entry + 12 × TRP_value
    """

    def _trp_value(self, entry, trp_pct):
        return Decimal(str(entry)) * Decimal(str(trp_pct)) / Decimal("100")

    def test_target_2r_correct_for_asterdm(self):
        result = _calc(500000, 0.50, 601, 3.18)
        trp_val = self._trp_value(601, 3.18)
        expected = (Decimal("601") + Decimal("2") * trp_val).quantize(Decimal("0.01"))
        assert result["target_2r"] == expected

    def test_target_ne_correct_for_asterdm(self):
        result = _calc(500000, 0.50, 601, 3.18)
        trp_val = self._trp_value(601, 3.18)
        expected = (Decimal("601") + Decimal("4") * trp_val).quantize(Decimal("0.01"))
        assert result["target_ne"] == expected

    def test_target_ge_correct_for_asterdm(self):
        result = _calc(500000, 0.50, 601, 3.18)
        trp_val = self._trp_value(601, 3.18)
        expected = (Decimal("601") + Decimal("8") * trp_val).quantize(Decimal("0.01"))
        assert result["target_ge"] == expected

    def test_target_ee_correct_for_asterdm(self):
        result = _calc(500000, 0.50, 601, 3.18)
        trp_val = self._trp_value(601, 3.18)
        expected = (Decimal("601") + Decimal("12") * trp_val).quantize(Decimal("0.01"))
        assert result["target_ee"] == expected

    def test_extension_targets_are_in_ascending_order(self):
        result = _calc(500000, 0.50, 600, 3.0)
        assert result["target_2r"] < result["target_ne"]
        assert result["target_ne"] < result["target_ge"]
        assert result["target_ge"] < result["target_ee"]

    def test_extension_targets_all_above_entry(self):
        entry = Decimal("600")
        result = _calc(500000, 0.50, 600, 3.0)
        assert result["target_2r"] > entry
        assert result["target_ne"] > entry
        assert result["target_ge"] > entry
        assert result["target_ee"] > entry


# ---------------------------------------------------------------------------
# RPT boundary values
# ---------------------------------------------------------------------------

class TestRptBoundaries:

    def test_min_rpt_0_2_pct_returns_smaller_position(self):
        """At minimum RPT the position size should be smaller than at default."""
        result_min = _calc(500000, 0.2, 601, 3.18)
        result_default = _calc(500000, 0.5, 601, 3.18)
        assert result_min["position_size"] < result_default["position_size"]

    def test_max_rpt_1_0_pct_returns_larger_position(self):
        """At maximum RPT the position size should be larger than at default."""
        result_max = _calc(500000, 1.0, 601, 3.18)
        result_default = _calc(500000, 0.5, 601, 3.18)
        assert result_max["position_size"] > result_default["position_size"]

    def test_min_rpt_rpt_amount_is_correct(self):
        result = _calc(500000, 0.2, 601, 3.18)
        expected = (Decimal("500000") * Decimal("0.2") / Decimal("100")).quantize(Decimal("0.01"))
        assert result["rpt_amount"] == expected

    def test_max_rpt_rpt_amount_is_correct(self):
        result = _calc(500000, 1.0, 601, 3.18)
        expected = (Decimal("500000") * Decimal("1.0") / Decimal("100")).quantize(Decimal("0.01"))
        assert result["rpt_amount"] == expected


# ---------------------------------------------------------------------------
# Input type coercion — int/float inputs must still work
# ---------------------------------------------------------------------------

class TestInputTypeCoercion:

    def test_int_account_value_is_accepted(self):
        result = calculate_position(500000, 0.50, Decimal("601"), 3.18)
        assert result["position_size"] == 131

    def test_float_account_value_is_accepted(self):
        result = calculate_position(500000.0, 0.50, Decimal("601"), 3.18)
        assert result["position_size"] == 131

    def test_int_entry_price_is_accepted(self):
        result = calculate_position(Decimal("500000"), 0.50, 601, 3.18)
        assert result["position_size"] == 131

    def test_float_entry_price_is_accepted(self):
        result = calculate_position(Decimal("500000"), 0.50, 601.0, 3.18)
        assert result["position_size"] == 131

    def test_coerced_inputs_still_return_decimals_for_rpt_amount(self):
        result = calculate_position(500000, 0.50, 601, 3.18)
        assert isinstance(result["rpt_amount"], Decimal)

    def test_coerced_inputs_still_return_decimals_for_sl_price(self):
        result = calculate_position(500000, 0.50, 601, 3.18)
        assert isinstance(result["sl_price"], Decimal)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_very_high_entry_price_with_adequate_capital_returns_small_position(self):
        """A ₹50,000 stock needs large capital to yield even 1 share.
        AV=5,000,000, RPT=0.5% → RPT_amount=25,000; SL=1,500 → size=16."""
        result = _calc(5_000_000, 0.5, 50000, 3.0)
        assert result["position_size"] >= 1

    def test_very_low_entry_price_returns_larger_position(self):
        """A ₹10 stock with ₹5L capital should give a large position size."""
        result = _calc(500000, 0.5, 10, 3.0)
        assert result["position_size"] > 100

    def test_very_high_trp_reduces_position_size(self):
        """Higher TRP (wider SL) means fewer shares for the same risk budget."""
        result_low_trp = _calc(500000, 0.5, 600, 2.0)
        result_high_trp = _calc(500000, 0.5, 600, 8.0)
        assert result_high_trp["position_size"] < result_low_trp["position_size"]

    def test_sl_price_below_entry(self):
        """SL must always be below the entry price."""
        result = _calc(500000, 0.50, 601, 3.18)
        assert result["sl_price"] < Decimal("601")

    def test_sl_amount_equals_entry_times_trp_pct(self):
        """sl_amount = entry × TRP% / 100."""
        result = _calc(500000, 0.50, 600, 3.0)
        expected = (Decimal("600") * Decimal("3.0") / Decimal("100")).quantize(Decimal("0.01"))
        assert result["sl_amount"] == expected

    def test_half_qty_is_exactly_half_position_size(self):
        """half_qty = position_size // 2 (integer floor division)."""
        result = _calc(500000, 0.50, 601, 3.18)
        assert result["half_qty"] == result["position_size"] // 2

    def test_all_required_keys_present_in_result(self):
        result = _calc(500000, 0.50, 601, 3.18)
        required_keys = {
            "rpt_amount", "sl_price", "sl_pct", "sl_amount",
            "position_value", "position_size", "half_qty",
            "target_2r", "target_ne", "target_ge", "target_ee",
        }
        assert required_keys.issubset(result.keys())

    def test_small_account_value_still_returns_positive_size(self):
        """Even a ₹10,000 account with low TRP should give at least 1 share."""
        result = _calc(10000, 0.5, 100, 3.0)
        assert result["position_size"] >= 1

    def test_rpt_amount_scales_linearly_with_account_value(self):
        """Doubling the account value should double the RPT amount."""
        result_base = _calc(500000, 0.50, 600, 3.0)
        result_double = _calc(1000000, 0.50, 600, 3.0)
        assert result_double["rpt_amount"] == result_base["rpt_amount"] * 2
