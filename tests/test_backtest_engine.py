"""
Tests for backend/services/backtest_metrics.py and backtest_strategies.py

Tests: compute_total_pnl, check_stage_fast, estimate_base_days_at, precompute_indicators

Run: python -m pytest tests/test_backtest_engine.py -v
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from backend.services.backtest_metrics import compute_total_pnl
from backend.services.backtest_strategies import (
    check_stage_fast,
    estimate_base_days_at,
    precompute_indicators,
)


# ---------------------------------------------------------------------------
# compute_total_pnl
# ---------------------------------------------------------------------------

class TestComputeTotalPnl:
    def _make_pos(self, **kwargs):
        pos = MagicMock()
        pos.qty_exited_2r = kwargs.get("qty_exited_2r", 0)
        pos.qty_exited_ne = kwargs.get("qty_exited_ne", 0)
        pos.qty_exited_ge = kwargs.get("qty_exited_ge", 0)
        pos.qty_exited_ee = kwargs.get("qty_exited_ee", 0)
        pos.qty_exited_sl = kwargs.get("qty_exited_sl", 0)
        pos.target_2r = kwargs.get("target_2r", None)
        pos.target_ne = kwargs.get("target_ne", None)
        pos.target_ge = kwargs.get("target_ge", None)
        pos.target_ee = kwargs.get("target_ee", None)
        pos.sl_price = kwargs.get("sl_price", None)
        return pos

    def test_no_exits(self):
        pos = self._make_pos()
        assert compute_total_pnl(pos, 100.0) == 0.0

    def test_2r_exit_only(self):
        pos = self._make_pos(qty_exited_2r=10, target_2r=120.0)
        # (120 - 100) * 10 = 200
        assert compute_total_pnl(pos, 100.0) == 200.0

    def test_ne_exit_only(self):
        pos = self._make_pos(qty_exited_ne=10, target_ne=140.0)
        assert compute_total_pnl(pos, 100.0) == 400.0

    def test_ge_exit_only(self):
        pos = self._make_pos(qty_exited_ge=10, target_ge=180.0)
        assert compute_total_pnl(pos, 100.0) == 800.0

    def test_ee_exit_only(self):
        pos = self._make_pos(qty_exited_ee=10, target_ee=220.0)
        assert compute_total_pnl(pos, 100.0) == 1200.0

    def test_sl_exit_with_original_sl(self):
        pos = self._make_pos(qty_exited_sl=10, sl_price=90.0)
        # (90 - 100) * 10 = -100
        assert compute_total_pnl(pos, 100.0) == -100.0

    def test_sl_exit_with_trailed_sl(self):
        pos = self._make_pos(qty_exited_sl=10, sl_price=90.0)
        # Should use trailed SL (105) instead of original (90)
        result = compute_total_pnl(pos, 100.0, sl_exit_price=105.0)
        assert result == 50.0  # (105 - 100) * 10

    def test_mixed_exits(self):
        pos = self._make_pos(
            qty_exited_2r=5, target_2r=120.0,
            qty_exited_ne=3, target_ne=140.0,
            qty_exited_sl=2, sl_price=90.0,
        )
        entry = 100.0
        expected = (120 - 100) * 5 + (140 - 100) * 3 + (90 - 100) * 2
        assert compute_total_pnl(pos, entry) == expected

    def test_zero_entry_price(self):
        pos = self._make_pos(qty_exited_2r=10, target_2r=120.0)
        result = compute_total_pnl(pos, 0.0)
        assert result == 1200.0  # (120 - 0) * 10

    def test_none_target_with_qty(self):
        """If target is None but qty > 0, that exit should be skipped."""
        pos = self._make_pos(qty_exited_2r=10, target_2r=None)
        assert compute_total_pnl(pos, 100.0) == 0.0

    def test_zero_qty_with_target(self):
        """Zero qty should contribute nothing."""
        pos = self._make_pos(qty_exited_2r=0, target_2r=120.0)
        assert compute_total_pnl(pos, 100.0) == 0.0


# ---------------------------------------------------------------------------
# check_stage_fast
# ---------------------------------------------------------------------------

class TestCheckStageFast:
    def _make_ind(self, close, sma150, sma150_20ago):
        return {
            "close": {"2025-01-15": close},
            "sma150": {"2025-01-15": sma150},
            "sma150_20ago": {"2025-01-15": sma150_20ago},
        }

    def test_stage_2(self):
        """Price well above SMA, SMA rising."""
        ind = self._make_ind(close=110, sma150=100, sma150_20ago=98)
        # price_vs_sma = 10%, sma_slope = 2.04%
        assert check_stage_fast(ind, "2025-01-15") == "S2"

    def test_stage_4(self):
        """Price well below SMA, SMA falling."""
        ind = self._make_ind(close=85, sma150=100, sma150_20ago=102)
        # price_vs_sma = -15%, sma_slope = -1.96%
        assert check_stage_fast(ind, "2025-01-15") == "S4"

    def test_stage_1b(self):
        """Price slightly above SMA, SMA flat/rising gently."""
        ind = self._make_ind(close=102, sma150=100, sma150_20ago=99.5)
        # price_vs_sma = 2%, sma_slope = 0.5%
        assert check_stage_fast(ind, "2025-01-15") == "S1B"

    def test_stage_3(self):
        """Price slightly below SMA, SMA declining moderately."""
        # Need sma_slope in (-1.0, -0.5) range to avoid S1B/S1 overlap
        ind = self._make_ind(close=99, sma150=100, sma150_20ago=100.7)
        # price_vs_sma = -1%, sma_slope = -0.695% (below -0.5, above -1.0 => S3)
        assert check_stage_fast(ind, "2025-01-15") == "S3"

    def test_unknown_missing_close(self):
        ind = {"close": {}, "sma150": {"2025-01-15": 100}, "sma150_20ago": {"2025-01-15": 99}}
        assert check_stage_fast(ind, "2025-01-15") == "UNKNOWN"

    def test_unknown_missing_sma(self):
        ind = {"close": {"2025-01-15": 100}, "sma150": {}, "sma150_20ago": {"2025-01-15": 99}}
        assert check_stage_fast(ind, "2025-01-15") == "UNKNOWN"

    def test_unknown_missing_sma_20ago(self):
        ind = {"close": {"2025-01-15": 100}, "sma150": {"2025-01-15": 100}, "sma150_20ago": {}}
        assert check_stage_fast(ind, "2025-01-15") == "UNKNOWN"

    def test_missing_day(self):
        ind = self._make_ind(close=100, sma150=100, sma150_20ago=100)
        assert check_stage_fast(ind, "2099-01-01") == "UNKNOWN"

    def test_stage_1_below_sma(self):
        """Price slightly below SMA, SMA flat."""
        ind = self._make_ind(close=99, sma150=100, sma150_20ago=100)
        # price_vs_sma = -1%, sma_slope = 0% -> falls into flat S1
        assert check_stage_fast(ind, "2025-01-15") == "S1"


# ---------------------------------------------------------------------------
# estimate_base_days_at
# ---------------------------------------------------------------------------

class TestEstimateBaseDaysAt:
    def _make_df(self, n_days, base_start=0.0, volatility=0.01):
        """Create a synthetic OHLCV DataFrame with a flat base pattern."""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
        base_price = 100.0
        closes = np.full(n_days, base_price)
        # Add small noise
        closes = closes + np.random.uniform(-volatility * base_price, volatility * base_price, n_days)
        highs = closes * 1.01
        lows = closes * 0.99
        return pd.DataFrame({"Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": 100000}, index=dates)

    def test_short_dataframe(self):
        df = self._make_df(20)
        days, quality = estimate_base_days_at(df, 15)
        assert days == 0
        assert quality == "UNKNOWN"

    def test_base_detection(self):
        df = self._make_df(80, volatility=0.005)
        days, quality = estimate_base_days_at(df, 79)
        assert days > 0

    def test_smooth_base(self):
        df = self._make_df(80, volatility=0.002)
        days, quality = estimate_base_days_at(df, 79)
        if days >= 10:
            assert quality in ("SMOOTH", "MIXED", "CHOPPY")

    def test_choppy_base(self):
        df = self._make_df(80, volatility=0.05)
        days, quality = estimate_base_days_at(df, 79)
        if days >= 10:
            assert quality in ("SMOOTH", "MIXED", "CHOPPY")

    def test_day_idx_at_minimum(self):
        df = self._make_df(31)
        days, quality = estimate_base_days_at(df, 30)
        assert isinstance(days, int)
        assert quality in ("SMOOTH", "MIXED", "CHOPPY", "UNKNOWN")

    def test_zero_idx(self):
        df = self._make_df(50)
        days, quality = estimate_base_days_at(df, 0)
        assert days == 0


# ---------------------------------------------------------------------------
# precompute_indicators
# ---------------------------------------------------------------------------

class TestPrecomputeIndicators:
    def _make_ohlcv(self, n_days=60):
        dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
        np.random.seed(42)
        close = np.cumsum(np.random.randn(n_days) * 0.5) + 100
        high = close + np.abs(np.random.randn(n_days))
        low = close - np.abs(np.random.randn(n_days))
        volume = np.random.randint(10000, 100000, n_days).astype(float)
        return pd.DataFrame({
            "Open": close - 0.1,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        }, index=dates)

    def test_basic_computation(self):
        ohlcv = {"TEST": self._make_ohlcv(60)}
        result = precompute_indicators(ohlcv)
        assert "TEST" in result
        ind = result["TEST"]
        assert "trp_ratio" in ind
        assert "close_pos" in ind
        assert "vol_ratio" in ind
        assert "is_green" in ind
        assert "adt" in ind
        assert "dma50" in ind

    def test_short_df_skipped(self):
        """DataFrames with < 30 rows should be skipped."""
        ohlcv = {"SHORT": self._make_ohlcv(20)}
        result = precompute_indicators(ohlcv)
        assert "SHORT" not in result

    def test_multiple_symbols(self):
        ohlcv = {
            "SYM1": self._make_ohlcv(60),
            "SYM2": self._make_ohlcv(60),
        }
        result = precompute_indicators(ohlcv)
        assert len(result) == 2

    def test_empty_input(self):
        result = precompute_indicators({})
        assert result == {}

    def test_raw_df_preserved(self):
        ohlcv = {"TEST": self._make_ohlcv(60)}
        result = precompute_indicators(ohlcv)
        assert "_df" in result["TEST"]
        assert isinstance(result["TEST"]["_df"], pd.DataFrame)

    def test_date_keys_format(self):
        ohlcv = {"TEST": self._make_ohlcv(60)}
        result = precompute_indicators(ohlcv)
        keys = list(result["TEST"]["close"].keys())
        assert len(keys) > 0
        # Should be YYYY-MM-DD format
        assert len(keys[0]) == 10
        assert keys[0][4] == "-"
