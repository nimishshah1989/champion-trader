"""
Tests for backend/intelligence/risk_guardian.py and risk_guardian_checks.py

Tests: freeze/unfreeze logic, trailing stop calculations,
       check_single_position, build_sector_map, fetch_prior_day_low

Run: python -m pytest tests/test_risk_guardian.py -v
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.intelligence.risk_guardian as rg
from backend.intelligence.risk_guardian import (
    is_frozen,
    unfreeze,
)
from backend.intelligence.risk_guardian_checks import (
    MONTH_DRAWDOWN_FREEZE_PCT,
    MAX_OPEN_RISK_PCT,
    PORTFOLIO_CHECK_INTERVAL_SECONDS,
    TRAIL_BREAKEVEN_THRESHOLD_R,
    TRAIL_2R_THRESHOLD_R,
    TRAIL_LOD_THRESHOLD_R,
    build_sector_map,
    check_single_position,
    fetch_prior_day_low,
)
import backend.intelligence.risk_guardian_checks as rgc


# ---------------------------------------------------------------------------
# freeze / unfreeze
# ---------------------------------------------------------------------------

class TestFreezeUnfreeze:
    def setup_method(self):
        """Reset module state before each test."""
        rg._frozen = False

    def test_initially_not_frozen(self):
        assert is_frozen() is False

    def test_freeze_state(self):
        rg._frozen = True
        assert is_frozen() is True

    def test_unfreeze(self):
        rg._frozen = True
        unfreeze()
        assert is_frozen() is False

    def test_unfreeze_when_not_frozen(self):
        """Unfreezing when not frozen should be safe."""
        unfreeze()
        assert is_frozen() is False


# ---------------------------------------------------------------------------
# build_sector_map
# ---------------------------------------------------------------------------

class TestBuildSectorMap:
    def test_with_stocks(self):
        mock_db = MagicMock()
        mock_stocks = [
            MagicMock(symbol="RELIANCE", sector="Oil & Gas"),
            MagicMock(symbol="TCS", sector="IT"),
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_stocks

        result = build_sector_map(mock_db, ["RELIANCE", "TCS"])
        assert result["RELIANCE"] == "Oil & Gas"
        assert result["TCS"] == "IT"

    def test_empty_symbols(self):
        mock_db = MagicMock()
        result = build_sector_map(mock_db, [])
        assert result == {}

    def test_missing_sector(self):
        mock_db = MagicMock()
        mock_stocks = [MagicMock(symbol="XYZ", sector=None)]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_stocks

        result = build_sector_map(mock_db, ["XYZ"])
        assert result["XYZ"] == "Unknown"

    def test_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB error")

        result = build_sector_map(mock_db, ["RELIANCE"])
        assert result == {}


# ---------------------------------------------------------------------------
# check_single_position — trailing stop logic
# ---------------------------------------------------------------------------

class TestCheckSinglePosition:
    def _make_trade(self, entry=100, sl=90, trp_pct=5.0, remaining_qty=100):
        trade = MagicMock()
        trade.sl_price = Decimal(str(sl))
        trade.avg_entry_price = Decimal(str(entry))
        trade.trp_at_entry = Decimal(str(trp_pct))
        trade.remaining_qty = remaining_qty
        trade.symbol = "TEST"
        return trade

    @pytest.mark.asyncio
    async def test_sl_breach_triggers_exit(self):
        trade = self._make_trade(entry=100, sl=90, trp_pct=5.0)
        live_price = 89  # Below SL of 90

        with patch.object(rgc, "execute_sl_exit", new_callable=AsyncMock) as mock_exit:
            with patch.object(rgc, "send_alert", new_callable=AsyncMock):
                await check_single_position(MagicMock(), trade, live_price)
                mock_exit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_breach_no_exit(self):
        trade = self._make_trade(entry=100, sl=90, trp_pct=5.0)
        live_price = 95  # Above SL

        with patch.object(rgc, "execute_sl_exit", new_callable=AsyncMock) as mock_exit:
            with patch.object(rgc, "fetch_prior_day_low", return_value=None):
                await check_single_position(MagicMock(), trade, live_price)
                mock_exit.assert_not_called()

    @pytest.mark.asyncio
    async def test_trail_to_breakeven(self):
        """When R >= 2, SL should trail to entry price."""
        trade = self._make_trade(entry=100, sl=90, trp_pct=5.0)
        # trp_value = 100 * 5/100 = 5
        # For 2R: price needs to be at entry + 2*trp = 100 + 10 = 110
        live_price = 111  # R = (111-100)/5 = 2.2

        with patch.object(rgc, "fetch_prior_day_low", return_value=None):
            await check_single_position(MagicMock(), trade, live_price)
            # SL should move to entry (100) from 90
            assert float(trade.sl_price) == 100.0

    @pytest.mark.asyncio
    async def test_trail_to_2r(self):
        """When R >= 4, SL should trail to 2R level."""
        trade = self._make_trade(entry=100, sl=90, trp_pct=5.0)
        # trp_value = 5, 4R = entry + 20 = 120
        live_price = 121  # R = (121-100)/5 = 4.2

        with patch.object(rgc, "fetch_prior_day_low", return_value=None):
            await check_single_position(MagicMock(), trade, live_price)
            # SL should be at entry + 2*trp = 110
            assert float(trade.sl_price) == 110.0

    @pytest.mark.asyncio
    async def test_trail_lod(self):
        """When R >= 8, SL should trail using prior day low."""
        trade = self._make_trade(entry=100, sl=90, trp_pct=5.0)
        # 8R = entry + 40 = 140
        live_price = 142  # R = (142-100)/5 = 8.4

        with patch.object(rgc, "fetch_prior_day_low", return_value=135.0):
            await check_single_position(MagicMock(), trade, live_price)
            # LOD = 135, which is > 90 (original SL)
            assert float(trade.sl_price) == 135.0

    @pytest.mark.asyncio
    async def test_sl_never_moves_down(self):
        """SL should only move up, never down."""
        trade = self._make_trade(entry=100, sl=105, trp_pct=5.0)
        # R = (111-100)/5 = 2.2 -> trail to breakeven (100)
        live_price = 111
        # But current SL is already at 105, so should stay at 105

        with patch.object(rgc, "fetch_prior_day_low", return_value=None):
            await check_single_position(MagicMock(), trade, live_price)
            # SL should NOT have changed since 100 < 105
            assert float(trade.sl_price) == 105.0

    @pytest.mark.asyncio
    async def test_zero_trp_skips(self):
        """If TRP is zero, skip the position."""
        trade = self._make_trade(entry=100, sl=90, trp_pct=0)
        live_price = 110

        with patch.object(rgc, "execute_sl_exit", new_callable=AsyncMock) as mock_exit:
            await check_single_position(MagicMock(), trade, live_price)
            mock_exit.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_entry_skips(self):
        trade = self._make_trade(entry=0, sl=0, trp_pct=5.0)
        live_price = 110

        with patch.object(rgc, "execute_sl_exit", new_callable=AsyncMock) as mock_exit:
            await check_single_position(MagicMock(), trade, live_price)
            mock_exit.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_prior_day_low
# ---------------------------------------------------------------------------

class TestFetchPriorDayLow:
    @patch("backend.intelligence.risk_guardian_checks.yf")
    def test_returns_low(self, mock_yf):
        import pandas as pd
        data = pd.DataFrame({
            "Low": [95.0, 96.0, 94.0, 97.0, 93.0],
        })
        data.columns = pd.Index(["Low"])
        mock_yf.download.return_value = data

        result = fetch_prior_day_low("RELIANCE")
        assert result == 97.0  # iloc[-2]

    @patch("backend.intelligence.risk_guardian_checks.yf")
    def test_insufficient_data(self, mock_yf):
        import pandas as pd
        data = pd.DataFrame({"Low": [95.0]})
        data.columns = pd.Index(["Low"])
        mock_yf.download.return_value = data

        result = fetch_prior_day_low("RELIANCE")
        assert result is None

    @patch("backend.intelligence.risk_guardian_checks.yf")
    def test_download_exception(self, mock_yf):
        mock_yf.download.side_effect = Exception("Network error")
        result = fetch_prior_day_low("RELIANCE")
        assert result is None


# ---------------------------------------------------------------------------
# Constants validation
# ---------------------------------------------------------------------------

class TestConstants:
    def test_trail_thresholds_ascending(self):
        assert TRAIL_BREAKEVEN_THRESHOLD_R < TRAIL_2R_THRESHOLD_R < TRAIL_LOD_THRESHOLD_R

    def test_max_risk_pct(self):
        assert MAX_OPEN_RISK_PCT == 10.0

    def test_freeze_threshold(self):
        assert MONTH_DRAWDOWN_FREEZE_PCT == 0.06

    def test_portfolio_check_interval(self):
        assert PORTFOLIO_CHECK_INTERVAL_SECONDS == 1800
