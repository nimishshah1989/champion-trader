"""
Tests for backend/intelligence/portfolio_math.py

Tests: calculate_open_risk, calculate_monthly_pnl, calculate_drawdown,
       calculate_var, calculate_correlation_matrix, calculate_sector_concentration

Run: python -m pytest tests/test_portfolio_math.py -v
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import patch

import pytest

from backend.intelligence.portfolio_math import (
    calculate_correlation_matrix,
    calculate_drawdown,
    calculate_monthly_pnl,
    calculate_open_risk,
    calculate_sector_concentration,
    calculate_var,
)


# ---------------------------------------------------------------------------
# calculate_open_risk
# ---------------------------------------------------------------------------

class TestCalculateOpenRisk:
    def test_single_position(self):
        positions = [
            {"symbol": "RELIANCE", "remaining_qty": 100, "avg_entry_price": 2500, "stop_loss": 2400}
        ]
        result = calculate_open_risk(positions, 500000)
        assert result["total_risk_amount"] == 10000.0
        assert result["total_risk_pct"] == 2.0
        assert result["exceeds_limit"] is False
        assert len(result["per_position"]) == 1

    def test_multiple_positions(self):
        positions = [
            {"symbol": "RELIANCE", "remaining_qty": 100, "avg_entry_price": 2500, "stop_loss": 2400},
            {"symbol": "INFY", "remaining_qty": 200, "avg_entry_price": 1500, "stop_loss": 1450},
        ]
        result = calculate_open_risk(positions, 500000)
        # RELIANCE: 100*(2500-2400) = 10000, INFY: 200*(1500-1450) = 10000
        assert result["total_risk_amount"] == 20000.0
        assert result["total_risk_pct"] == 4.0

    def test_exceeds_limit(self):
        positions = [
            {"symbol": "RELIANCE", "remaining_qty": 1000, "avg_entry_price": 2500, "stop_loss": 2200},
        ]
        # Risk = 1000 * 300 = 300000, which is 60% of 500000
        result = calculate_open_risk(positions, 500000)
        assert result["exceeds_limit"] is True

    def test_empty_positions(self):
        result = calculate_open_risk([], 500000)
        assert result["total_risk_amount"] == 0.0
        assert result["total_risk_pct"] == 0.0
        assert result["exceeds_limit"] is False

    def test_zero_account_value(self):
        positions = [
            {"symbol": "X", "remaining_qty": 10, "avg_entry_price": 100, "stop_loss": 90}
        ]
        result = calculate_open_risk(positions, 0)
        assert result["total_risk_pct"] == 0

    def test_zero_qty(self):
        positions = [
            {"symbol": "X", "remaining_qty": 0, "avg_entry_price": 100, "stop_loss": 90}
        ]
        result = calculate_open_risk(positions, 500000)
        assert result["total_risk_amount"] == 0.0

    def test_none_values(self):
        positions = [
            {"symbol": "X", "remaining_qty": None, "avg_entry_price": None, "stop_loss": None}
        ]
        result = calculate_open_risk(positions, 500000)
        assert result["total_risk_amount"] == 0.0

    def test_missing_keys(self):
        positions = [{"symbol": "X"}]
        result = calculate_open_risk(positions, 500000)
        assert result["total_risk_amount"] == 0.0

    def test_decimal_account_value(self):
        """account_value may be Decimal from config."""
        positions = [
            {"symbol": "RELIANCE", "remaining_qty": 100, "avg_entry_price": 2500, "stop_loss": 2400}
        ]
        result = calculate_open_risk(positions, Decimal("500000"))
        assert result["total_risk_amount"] == 10000.0

    def test_per_position_detail(self):
        positions = [
            {"symbol": "ABC", "remaining_qty": 50, "avg_entry_price": 200, "stop_loss": 190}
        ]
        result = calculate_open_risk(positions, 100000)
        pp = result["per_position"][0]
        assert pp["symbol"] == "ABC"
        assert pp["risk_amount"] == 500.0  # 50 * 10
        assert pp["risk_pct"] == 0.5  # 500/100000 * 100


# ---------------------------------------------------------------------------
# calculate_monthly_pnl
# ---------------------------------------------------------------------------

class TestCalculateMonthlyPnl:
    def _today_str(self):
        return datetime.now().strftime("%Y-%m-%d")

    def test_single_winning_trade(self):
        trades = [
            {"exit_date": self._today_str(), "total_pnl": 5000, "status": "CLOSED"}
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_pnl"] == 5000.0
        assert result["mtd_trades"] == 1
        assert result["mtd_wins"] == 1
        assert result["mtd_losses"] == 0

    def test_winning_and_losing(self):
        today = self._today_str()
        trades = [
            {"exit_date": today, "total_pnl": 5000, "status": "CLOSED"},
            {"exit_date": today, "total_pnl": -2000, "status": "CLOSED"},
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_pnl"] == 3000.0
        assert result["mtd_wins"] == 1
        assert result["mtd_losses"] == 1
        assert result["mtd_win_rate"] == 0.5

    def test_empty_trades(self):
        result = calculate_monthly_pnl([])
        assert result["mtd_pnl"] == 0.0
        assert result["mtd_trades"] == 0

    def test_old_trades_excluded(self):
        trades = [
            {"exit_date": "2020-01-15", "total_pnl": 10000, "status": "CLOSED"}
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_pnl"] == 0.0
        assert result["mtd_trades"] == 0

    def test_open_trades_excluded(self):
        trades = [
            {"exit_date": self._today_str(), "total_pnl": 5000, "status": "OPEN"}
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_trades"] == 0

    def test_stopped_trades_included(self):
        trades = [
            {"exit_date": self._today_str(), "total_pnl": -3000, "status": "STOPPED"}
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_pnl"] == -3000.0
        assert result["mtd_trades"] == 1

    def test_none_pnl_treated_as_zero(self):
        trades = [
            {"exit_date": self._today_str(), "total_pnl": None, "status": "CLOSED"}
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_pnl"] == 0.0
        assert result["mtd_losses"] == 1  # 0 is not > 0, so counted as loss

    def test_no_exit_date(self):
        trades = [
            {"exit_date": None, "total_pnl": 5000, "status": "CLOSED"}
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_trades"] == 0

    def test_win_rate_100_pct(self):
        today = self._today_str()
        trades = [
            {"exit_date": today, "total_pnl": 1000, "status": "CLOSED"},
            {"exit_date": today, "total_pnl": 2000, "status": "CLOSED"},
        ]
        result = calculate_monthly_pnl(trades)
        assert result["mtd_win_rate"] == 1.0


# ---------------------------------------------------------------------------
# calculate_drawdown
# ---------------------------------------------------------------------------

class TestCalculateDrawdown:
    def test_no_drawdown(self):
        curve = [100, 101, 102, 103, 104]
        result = calculate_drawdown(curve)
        assert result["max_drawdown_pct"] == 0.0

    def test_simple_drawdown(self):
        curve = [100, 110, 90, 95]
        result = calculate_drawdown(curve)
        # Peak 110, trough 90, dd = 20/110 ~= 0.1818
        assert result["max_drawdown_pct"] > 0.15
        assert result["max_drawdown_amount"] == 20.0

    def test_empty_curve(self):
        result = calculate_drawdown([])
        assert result["max_drawdown_pct"] == 0.0

    def test_single_point(self):
        result = calculate_drawdown([100])
        assert result["max_drawdown_pct"] == 0.0

    def test_recovery(self):
        curve = [100, 110, 90, 120]
        result = calculate_drawdown(curve)
        assert result["current_drawdown_pct"] == 0.0

    def test_ongoing_drawdown(self):
        curve = [100, 110, 95]
        result = calculate_drawdown(curve)
        assert result["current_drawdown_pct"] > 0


# ---------------------------------------------------------------------------
# calculate_var
# ---------------------------------------------------------------------------

class TestCalculateVar:
    def test_basic_var(self):
        values = [50000, 50000]
        returns = [
            [0.01, -0.02, 0.005, -0.01, 0.003, -0.015, 0.02, -0.005, 0.01, -0.008],
            [0.005, -0.01, 0.003, -0.02, 0.01, -0.005, 0.015, -0.01, 0.005, -0.012],
        ]
        result = calculate_var(values, returns)
        assert result >= 0

    def test_empty_positions(self):
        assert calculate_var([], []) == 0.0

    def test_empty_returns(self):
        assert calculate_var([50000], []) == 0.0

    def test_short_returns(self):
        """Returns shorter than 5 should return 0."""
        assert calculate_var([50000], [[0.01, -0.02]]) == 0.0

    def test_zero_position_values(self):
        assert calculate_var([0, 0], [[0.01, 0.02, 0.03, 0.04, 0.05], [0.01, 0.02, 0.03, 0.04, 0.05]]) == 0.0


# ---------------------------------------------------------------------------
# calculate_correlation_matrix
# ---------------------------------------------------------------------------

class TestCalculateCorrelationMatrix:
    def test_two_symbols(self):
        returns = {
            "A": [0.01, -0.02, 0.005] * 5,
            "B": [0.01, -0.02, 0.005] * 5,
        }
        result = calculate_correlation_matrix(returns)
        assert "A" in result
        assert result["A"]["A"] == pytest.approx(1.0, abs=0.01)

    def test_single_symbol(self):
        returns = {"A": [0.01] * 20}
        result = calculate_correlation_matrix(returns)
        assert result == {}

    def test_short_series(self):
        returns = {"A": [0.01], "B": [0.02]}
        result = calculate_correlation_matrix(returns)
        assert result == {}


# ---------------------------------------------------------------------------
# calculate_sector_concentration
# ---------------------------------------------------------------------------

class TestCalculateSectorConcentration:
    def test_no_concentration(self):
        positions = [
            {"symbol": "A", "sector": "IT"},
            {"symbol": "B", "sector": "Pharma"},
        ]
        result = calculate_sector_concentration(positions)
        assert result["has_concentration_risk"] is False
        assert result["concentrated_sectors"] == []

    def test_concentration_detected(self):
        positions = [
            {"symbol": "A", "sector": "IT"},
            {"symbol": "B", "sector": "IT"},
            {"symbol": "C", "sector": "Pharma"},
        ]
        result = calculate_sector_concentration(positions)
        assert result["has_concentration_risk"] is True
        assert len(result["concentrated_sectors"]) == 1
        assert result["concentrated_sectors"][0]["sector"] == "IT"
        assert result["concentrated_sectors"][0]["count"] == 2

    def test_empty_positions(self):
        result = calculate_sector_concentration([])
        assert result["has_concentration_risk"] is False

    def test_multiple_concentrated_sectors(self):
        positions = [
            {"symbol": "A", "sector": "IT"},
            {"symbol": "B", "sector": "IT"},
            {"symbol": "C", "sector": "Pharma"},
            {"symbol": "D", "sector": "Pharma"},
        ]
        result = calculate_sector_concentration(positions)
        assert len(result["concentrated_sectors"]) == 2

    def test_unknown_sector(self):
        positions = [
            {"symbol": "A", "sector": "Unknown"},
            {"symbol": "B", "sector": "Unknown"},
        ]
        result = calculate_sector_concentration(positions)
        assert result["has_concentration_risk"] is True
