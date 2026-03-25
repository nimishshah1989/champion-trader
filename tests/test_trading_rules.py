"""
Tests for backend/services/trading_rules.py

Verifies that the TRADING_RULES dict and ALERT_TEMPLATES contain the
correct non-negotiable values from the Champion Trader methodology.

Run: python -m pytest tests/test_trading_rules.py -v
"""
from __future__ import annotations

import pytest

from backend.services.trading_rules import ALERT_TEMPLATES, TRADING_RULES


# ---------------------------------------------------------------------------
# Key presence
# ---------------------------------------------------------------------------

class TestRequiredKeys:
    """All required keys must exist in TRADING_RULES."""

    REQUIRED_KEYS = [
        "max_rpt_pct",
        "min_rpt_pct",
        "default_rpt_pct",
        "max_open_risk_pct",
        "entry_split",
        "min_base_bars",
        "min_trp",
        "mathematical_exit_r",
        "mathematical_exit_pct",
        "normal_extension_x",
        "great_extension_x",
        "extreme_extension_x",
        "ne_exit_pct",
        "ge_exit_pct",
        "ee_exit_pct",
        "ppc_min_volume_ratio",
        "ppc_min_trp_ratio",
        "ppc_min_close_position",
        "entry_window_minutes_before_close",
    ]

    @pytest.mark.parametrize("key", REQUIRED_KEYS)
    def test_required_key_exists(self, key):
        assert key in TRADING_RULES, f"Missing required key: {key}"


# ---------------------------------------------------------------------------
# RPT limits
# ---------------------------------------------------------------------------

class TestRptLimits:

    def test_min_rpt_pct_is_0_2(self):
        assert TRADING_RULES["min_rpt_pct"] == 0.2

    def test_max_rpt_pct_is_1_0(self):
        assert TRADING_RULES["max_rpt_pct"] == 1.0

    def test_default_rpt_pct_is_0_5(self):
        assert TRADING_RULES["default_rpt_pct"] == 0.5

    def test_default_rpt_within_bounds(self):
        assert (
            TRADING_RULES["min_rpt_pct"]
            <= TRADING_RULES["default_rpt_pct"]
            <= TRADING_RULES["max_rpt_pct"]
        )


# ---------------------------------------------------------------------------
# Open risk and position sizing
# ---------------------------------------------------------------------------

class TestOpenRiskAndSizing:

    def test_max_open_risk_pct_is_10(self):
        assert TRADING_RULES["max_open_risk_pct"] == 10.0

    def test_entry_split_is_50_50(self):
        assert TRADING_RULES["entry_split"] == 0.5

    def test_entry_split_represents_half(self):
        """entry_split of 0.5 means first half entered at trigger."""
        assert TRADING_RULES["entry_split"] == 0.5


# ---------------------------------------------------------------------------
# Base quality rules
# ---------------------------------------------------------------------------

class TestBaseQualityRules:

    def test_min_base_bars_is_20(self):
        assert TRADING_RULES["min_base_bars"] == 20

    def test_min_trp_is_2(self):
        assert TRADING_RULES["min_trp"] == 2.0


# ---------------------------------------------------------------------------
# Exit framework
# ---------------------------------------------------------------------------

class TestExitFramework:

    def test_mathematical_exit_at_2r(self):
        assert TRADING_RULES["mathematical_exit_r"] == 2

    def test_mathematical_exit_pct_is_20(self):
        assert TRADING_RULES["mathematical_exit_pct"] == 0.20

    def test_ne_multiplier_is_4(self):
        assert TRADING_RULES["normal_extension_x"] == 4

    def test_ge_multiplier_is_8(self):
        assert TRADING_RULES["great_extension_x"] == 8

    def test_ee_multiplier_is_12(self):
        assert TRADING_RULES["extreme_extension_x"] == 12

    def test_ne_exit_pct_is_20(self):
        assert TRADING_RULES["ne_exit_pct"] == 0.20

    def test_ge_exit_pct_is_40(self):
        assert TRADING_RULES["ge_exit_pct"] == 0.40

    def test_ee_exit_pct_is_80(self):
        assert TRADING_RULES["ee_exit_pct"] == 0.80

    def test_extension_multipliers_are_ascending(self):
        assert (
            TRADING_RULES["mathematical_exit_r"]
            < TRADING_RULES["normal_extension_x"]
            < TRADING_RULES["great_extension_x"]
            < TRADING_RULES["extreme_extension_x"]
        )

    def test_exit_percentages_are_ascending(self):
        assert (
            TRADING_RULES["mathematical_exit_pct"]
            <= TRADING_RULES["ne_exit_pct"]
            < TRADING_RULES["ge_exit_pct"]
            < TRADING_RULES["ee_exit_pct"]
        )


# ---------------------------------------------------------------------------
# PPC volume/range filters
# ---------------------------------------------------------------------------

class TestPpcFilters:

    def test_ppc_min_volume_ratio_is_1_5(self):
        assert TRADING_RULES["ppc_min_volume_ratio"] == 1.5

    def test_ppc_min_trp_ratio_is_1_5(self):
        assert TRADING_RULES["ppc_min_trp_ratio"] == 1.5

    def test_ppc_min_close_position_is_0_60(self):
        assert TRADING_RULES["ppc_min_close_position"] == 0.60


# ---------------------------------------------------------------------------
# Alert templates
# ---------------------------------------------------------------------------

class TestAlertTemplates:
    """Every template must exist and contain its required format placeholders."""

    def test_sl_hit_template_exists(self):
        assert "SL_HIT" in ALERT_TEMPLATES

    def test_sl_hit_contains_symbol_placeholder(self):
        assert "{symbol}" in ALERT_TEMPLATES["SL_HIT"]

    def test_sl_hit_contains_sl_price_placeholder(self):
        assert "{sl_price}" in ALERT_TEMPLATES["SL_HIT"]

    def test_trigger_level_template_exists(self):
        assert "TRIGGER_LEVEL" in ALERT_TEMPLATES

    def test_trigger_level_contains_symbol_placeholder(self):
        assert "{symbol}" in ALERT_TEMPLATES["TRIGGER_LEVEL"]

    def test_trigger_level_contains_tl_placeholder(self):
        assert "{tl}" in ALERT_TEMPLATES["TRIGGER_LEVEL"]

    def test_ppc_detected_template_exists(self):
        assert "PPC_DETECTED" in ALERT_TEMPLATES

    def test_ppc_detected_contains_symbol_placeholder(self):
        assert "{symbol}" in ALERT_TEMPLATES["PPC_DETECTED"]

    def test_ppc_detected_contains_trp_ratio_placeholder(self):
        assert "{trp_ratio}" in ALERT_TEMPLATES["PPC_DETECTED"]

    def test_ppc_detected_contains_vol_ratio_placeholder(self):
        assert "{vol_ratio}" in ALERT_TEMPLATES["PPC_DETECTED"]

    def test_2r_hit_template_exists(self):
        assert "2R_HIT" in ALERT_TEMPLATES

    def test_2r_hit_contains_symbol_placeholder(self):
        assert "{symbol}" in ALERT_TEMPLATES["2R_HIT"]

    def test_2r_hit_contains_target_placeholder(self):
        assert "{target}" in ALERT_TEMPLATES["2R_HIT"]

    def test_extension_template_exists(self):
        assert "EXTENSION" in ALERT_TEMPLATES

    def test_extension_contains_ext_type_placeholder(self):
        assert "{ext_type}" in ALERT_TEMPLATES["EXTENSION"]

    def test_extension_contains_symbol_placeholder(self):
        assert "{symbol}" in ALERT_TEMPLATES["EXTENSION"]

    def test_extension_contains_price_placeholder(self):
        assert "{price}" in ALERT_TEMPLATES["EXTENSION"]

    def test_earnings_warning_template_exists(self):
        assert "EARNINGS_WARNING" in ALERT_TEMPLATES

    def test_earnings_warning_contains_symbol_placeholder(self):
        assert "{symbol}" in ALERT_TEMPLATES["EARNINGS_WARNING"]

    def test_earnings_warning_contains_days_placeholder(self):
        assert "{days}" in ALERT_TEMPLATES["EARNINGS_WARNING"]

    def test_market_stance_template_exists(self):
        assert "MARKET_STANCE" in ALERT_TEMPLATES

    def test_market_stance_contains_stance_placeholder(self):
        assert "{stance}" in ALERT_TEMPLATES["MARKET_STANCE"]

    def test_market_stance_contains_rpt_pct_placeholder(self):
        assert "{rpt_pct}" in ALERT_TEMPLATES["MARKET_STANCE"]

    def test_alert_templates_are_all_non_empty_strings(self):
        for key, value in ALERT_TEMPLATES.items():
            assert isinstance(value, str) and len(value) > 0, (
                f"Template '{key}' is empty or not a string"
            )

    def test_all_templates_can_be_formatted_with_dummy_values(self):
        """Smoke-test: all templates must be valid Python format strings."""
        dummy_values = {
            "symbol": "TEST",
            "sl_price": "100.00",
            "tl": "105.00",
            "trp_ratio": "1.8",
            "vol_ratio": "2.0",
            "target": "120.00",
            "ext_type": "NE",
            "ext_label": "NE",
            "price": "110.00",
            "days": "5",
            "stance": "BULLISH",
            "rpt_pct": "0.5",
            "strong": "NIFTY50",
            "weak": "REALTY",
        }
        for key, template in ALERT_TEMPLATES.items():
            try:
                formatted = template.format(**dummy_values)
                assert len(formatted) > 0
            except KeyError as exc:
                pytest.fail(
                    f"Template '{key}' has placeholder {exc} not in dummy_values"
                )
