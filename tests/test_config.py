"""
Tests for backend/config.py

Settings are tested by instantiating Settings() directly (without a .env file)
so we exercise the default values defined in the class body.

Run: python -m pytest tests/test_config.py -v
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helper: create a Settings instance with no .env side-effects
# ---------------------------------------------------------------------------

def _fresh_settings(**overrides):
    """
    Instantiate Settings with the environment cleared of any CTS-specific vars,
    applying overrides as explicit kwargs.  env_file is disabled so the real
    .env on disk (if present) cannot affect default-value tests.
    """
    # Temporarily clear known env vars that would shadow defaults
    env_keys_to_clear = [
        "DATABASE_URL",
        "DEFAULT_ACCOUNT_VALUE",
        "DEFAULT_RPT_PCT",
        "AUTOOPTIMIZE_ENABLED",
        "ENVIRONMENT",
        "BROKER_LIVE_TRADING",
        "APP_PORT",
    ]
    clean_env = {k: v for k, v in os.environ.items() if k not in env_keys_to_clear}

    with patch.dict(os.environ, clean_env, clear=True):
        # Pass _env_file=None to suppress pydantic-settings from reading disk
        from backend.config import Settings  # import inside patch context
        return Settings(_env_file=None, **overrides)


# ---------------------------------------------------------------------------
# Default value tests
# ---------------------------------------------------------------------------

class TestSettingsDefaults:

    def test_database_url_defaults_to_sqlite(self):
        s = _fresh_settings()
        assert "sqlite" in s.database_url

    def test_default_account_value_is_decimal(self):
        s = _fresh_settings()
        assert isinstance(s.default_account_value, Decimal)

    def test_default_account_value_is_1000000(self):
        s = _fresh_settings()
        assert s.default_account_value == Decimal("1000000")

    def test_default_rpt_pct_is_0_50(self):
        s = _fresh_settings()
        assert s.default_rpt_pct == 0.50

    def test_default_rpt_pct_is_numeric(self):
        # Pydantic v2 may coerce float fields to Decimal when the default
        # literal is parsed alongside Decimal fields; accept both.
        s = _fresh_settings()
        assert isinstance(s.default_rpt_pct, (float, Decimal))

    def test_autooptimize_enabled_defaults_false_frozen_for_v2(self):
        # FROZEN for the v2 rollout: auto-tuning must not perturb the parity-gated config.
        s = _fresh_settings()
        assert s.autooptimize_enabled is False

    def test_environment_defaults_development(self):
        s = _fresh_settings()
        assert s.environment == "development"

    def test_app_port_defaults_8000(self):
        s = _fresh_settings()
        assert s.app_port == 8000

    def test_broker_live_trading_defaults_false(self):
        s = _fresh_settings()
        assert s.broker_live_trading is False

    def test_broker_type_defaults_paper(self):
        s = _fresh_settings()
        assert s.broker_type == "paper"

    def test_default_exchange_is_nse(self):
        s = _fresh_settings()
        assert s.default_exchange == "NSE"

    def test_autooptimize_start_hour_defaults_18(self):
        s = _fresh_settings()
        assert s.autooptimize_start_hour == 18

    def test_autooptimize_halt_hour_defaults_8(self):
        s = _fresh_settings()
        assert s.autooptimize_halt_hour == 8


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------

class TestSettingsOverrides:
    """Verify that environment variables correctly override defaults."""

    def test_environment_override_production(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
            from importlib import reload
            import backend.config as cfg_module
            s = cfg_module.Settings(_env_file=None)
            assert s.environment == "production"

    def test_app_port_override(self):
        with patch.dict(os.environ, {"APP_PORT": "9000"}, clear=False):
            from importlib import reload
            import backend.config as cfg_module
            s = cfg_module.Settings(_env_file=None)
            assert s.app_port == 9000

    def test_autooptimize_disabled_via_env(self):
        with patch.dict(os.environ, {"AUTOOPTIMIZE_ENABLED": "false"}, clear=False):
            import backend.config as cfg_module
            s = cfg_module.Settings(_env_file=None)
            assert s.autooptimize_enabled is False

    def test_default_account_value_override(self):
        with patch.dict(os.environ, {"DEFAULT_ACCOUNT_VALUE": "2000000"}, clear=False):
            import backend.config as cfg_module
            s = cfg_module.Settings(_env_file=None)
            assert s.default_account_value == Decimal("2000000")


# ---------------------------------------------------------------------------
# Singleton settings object
# ---------------------------------------------------------------------------

class TestSettingsModule:

    def test_settings_singleton_exists(self):
        from backend.config import settings
        assert settings is not None

    def test_settings_singleton_is_settings_instance(self):
        from backend.config import settings, Settings
        assert isinstance(settings, Settings)

    def test_settings_singleton_has_default_account_value(self):
        from backend.config import settings
        assert hasattr(settings, "default_account_value")

    def test_settings_singleton_has_default_rpt_pct(self):
        from backend.config import settings
        assert hasattr(settings, "default_rpt_pct")

    def test_settings_singleton_has_autooptimize_enabled(self):
        from backend.config import settings
        assert hasattr(settings, "autooptimize_enabled")

    def test_settings_singleton_default_account_value_is_decimal(self):
        from backend.config import settings
        assert isinstance(settings.default_account_value, Decimal)
