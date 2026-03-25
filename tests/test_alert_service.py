"""
Tests for backend/services/alert_service.py

Tests: create_alert function with various alert types, custom titles, data payloads.

Run: python -m pytest tests/test_alert_service.py -v
"""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import MagicMock, patch, call

import pytest

from backend.services.alert_service import (
    ALERT_CONFIG,
    create_alert,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    db = MagicMock()
    # Make refresh set an id on the alert
    def _refresh(obj):
        obj.id = 42
    db.refresh.side_effect = _refresh
    return db


# ---------------------------------------------------------------------------
# create_alert
# ---------------------------------------------------------------------------

class TestCreateAlert:
    def test_basic_alert(self, mock_db):
        alert = create_alert(mock_db, "SL_HIT", "Price hit SL", symbol="RELIANCE")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_sl_hit_default_title(self, mock_db):
        alert = create_alert(mock_db, "SL_HIT", "Test", symbol="INFY")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.title == "SL Alert: INFY"
        assert added_obj.severity == "critical"

    def test_trigger_level_default_title(self, mock_db):
        alert = create_alert(mock_db, "TRIGGER_LEVEL", "Broke trigger", symbol="TCS")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.title == "Entry Alert: TCS"
        assert added_obj.severity == "warning"

    def test_ppc_detected(self, mock_db):
        alert = create_alert(mock_db, "PPC_DETECTED", "PPC found", symbol="HDFC")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.title == "PPC Detected: HDFC"
        assert added_obj.severity == "info"

    def test_custom_title_overrides_default(self, mock_db):
        alert = create_alert(mock_db, "SL_HIT", "msg", symbol="X", title="Custom Title")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.title == "Custom Title"

    def test_no_symbol(self, mock_db):
        alert = create_alert(mock_db, "MARKET_STANCE", "Market is bullish")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.title == "Market Stance Update"
        assert added_obj.symbol is None

    def test_system_alert(self, mock_db):
        alert = create_alert(mock_db, "SYSTEM", "System startup complete")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.title == "System Alert"

    def test_unknown_alert_type(self, mock_db):
        """Unknown type should default to severity=info."""
        alert = create_alert(mock_db, "UNKNOWN_TYPE", "Something happened")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.severity == "info"
        assert added_obj.title == "Alert"

    def test_data_payload_serialized(self, mock_db):
        data = {"target": "500.00", "r_multiple": 2.5}
        alert = create_alert(mock_db, "2R_HIT", "2R hit", symbol="X", data=data)
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.data == json.dumps(data)

    def test_none_data(self, mock_db):
        alert = create_alert(mock_db, "SL_HIT", "msg", symbol="X")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.data is None

    def test_all_alert_types_have_config(self):
        """Every type in ALERT_CONFIG should have severity and title_template."""
        for alert_type, config in ALERT_CONFIG.items():
            assert "severity" in config, f"{alert_type} missing severity"
            assert "title_template" in config, f"{alert_type} missing title_template"

    def test_alert_types_count(self):
        """Ensure we have configs for all expected alert types."""
        expected = {"SL_HIT", "TRIGGER_LEVEL", "PPC_DETECTED", "NPC_DETECTED",
                    "CONTRACTION", "2R_HIT", "EXTENSION", "EARNINGS_WARNING",
                    "MARKET_STANCE", "SYSTEM"}
        assert set(ALERT_CONFIG.keys()) == expected

    def test_empty_symbol_in_template(self, mock_db):
        alert = create_alert(mock_db, "SL_HIT", "msg")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.title == "SL Alert: "

    def test_message_stored(self, mock_db):
        alert = create_alert(mock_db, "SYSTEM", "The message content")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.message == "The message content"

    def test_alert_type_stored(self, mock_db):
        alert = create_alert(mock_db, "NPC_DETECTED", "msg", symbol="Z")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.alert_type == "NPC_DETECTED"
