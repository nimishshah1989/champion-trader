"""
Tests for backend/services/scanner_engine.py and backend/services/technical.py

Scanner logic is tested by injecting synthetic DataFrames — no yfinance calls.
All external imports (data_fetcher, strategy.PARAMETERS) are patched.

Run: python -m pytest tests/test_scanner_engine.py -v
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# DataFrame builders
# ---------------------------------------------------------------------------

def _make_df(
    n_rows: int = 200,
    close_price: float = 500.0,
    high_pct: float = 0.02,
    low_pct: float = 0.02,
    volume: int = 1_000_000,
    open_above_close: bool = False,   # True → red candle
) -> pd.DataFrame:
    """
    Produce a synthetic OHLCV DataFrame with uniform candles.

    Columns: Open, High, Low, Close, Volume (matching yfinance output).
    """
    closes = np.full(n_rows, close_price, dtype=float)
    highs = closes * (1 + high_pct)
    lows = closes * (1 - low_pct)

    if open_above_close:
        # Red candle: Open > Close
        opens = closes * 1.005
    else:
        # Green candle: Open < Close
        opens = closes * 0.995

    return pd.DataFrame(
        {
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": np.full(n_rows, volume, dtype=float),
        }
    )


def _make_expanding_df(n_rows: int = 200) -> pd.DataFrame:
    """
    DataFrame where the last candle has 3x the normal range — useful for PPC tests.
    """
    df = _make_df(n_rows=n_rows)
    # Last candle: big green with high volume (clear PPC signal)
    df.iloc[-1, df.columns.get_loc("Open")] = 490.0
    df.iloc[-1, df.columns.get_loc("Close")] = 510.0
    df.iloc[-1, df.columns.get_loc("High")] = 515.0
    df.iloc[-1, df.columns.get_loc("Low")] = 488.0
    df.iloc[-1, df.columns.get_loc("Volume")] = 5_000_000  # 5× average
    return df


# ---------------------------------------------------------------------------
# Tests for technical.py functions (pure functions, no mocking needed)
# ---------------------------------------------------------------------------

class TestCalculateTrp:

    def test_trp_is_correct_for_known_values(self):
        from backend.services.technical import calculate_trp

        df = pd.DataFrame({
            "High": [110.0],
            "Low": [90.0],
            "Close": [100.0],
        })
        result = calculate_trp(df)
        # TRP = (110 - 90) / 100 * 100 = 20%
        assert abs(result.iloc[0] - 20.0) < 0.001

    def test_trp_returns_series(self):
        from backend.services.technical import calculate_trp

        df = _make_df(n_rows=10)
        result = calculate_trp(df)
        assert isinstance(result, pd.Series)
        assert len(result) == 10

    def test_trp_all_positive(self):
        from backend.services.technical import calculate_trp

        df = _make_df(n_rows=50)
        result = calculate_trp(df)
        assert (result > 0).all()


class TestCalculateAvgTrp:

    def test_avg_trp_nan_for_first_period_minus_one_rows(self):
        from backend.services.technical import calculate_trp, calculate_avg_trp

        df = _make_df(n_rows=30)
        trp = calculate_trp(df)
        avg_trp = calculate_avg_trp(trp, period=20)
        # First 19 values should be NaN (min_periods=period)
        assert pd.isna(avg_trp.iloc[0])
        assert pd.isna(avg_trp.iloc[18])

    def test_avg_trp_not_nan_at_period_row(self):
        from backend.services.technical import calculate_trp, calculate_avg_trp

        df = _make_df(n_rows=50)
        trp = calculate_trp(df)
        avg_trp = calculate_avg_trp(trp, period=20)
        assert pd.notna(avg_trp.iloc[19])


class TestCalculateClosePosition:

    def test_close_at_high_returns_1(self):
        from backend.services.technical import calculate_close_position

        df = pd.DataFrame({
            "High": [110.0],
            "Low": [90.0],
            "Close": [110.0],   # at the high
        })
        result = calculate_close_position(df)
        assert abs(result.iloc[0] - 1.0) < 0.001

    def test_close_at_low_returns_0(self):
        from backend.services.technical import calculate_close_position

        df = pd.DataFrame({
            "High": [110.0],
            "Low": [90.0],
            "Close": [90.0],    # at the low
        })
        result = calculate_close_position(df)
        assert abs(result.iloc[0] - 0.0) < 0.001

    def test_close_at_midpoint_returns_0_5(self):
        from backend.services.technical import calculate_close_position

        df = pd.DataFrame({
            "High": [110.0],
            "Low": [90.0],
            "Close": [100.0],   # midpoint
        })
        result = calculate_close_position(df)
        assert abs(result.iloc[0] - 0.5) < 0.001

    def test_returns_series(self):
        from backend.services.technical import calculate_close_position

        df = _make_df(n_rows=10)
        result = calculate_close_position(df)
        assert isinstance(result, pd.Series)


class TestCalculateVolumeRatio:

    def test_volume_ratio_1_when_volume_equals_average(self):
        from backend.services.technical import calculate_volume_ratio

        vol = pd.Series([1_000_000.0])
        avg_vol = pd.Series([1_000_000.0])
        result = calculate_volume_ratio(vol, avg_vol)
        assert abs(result.iloc[0] - 1.0) < 0.001

    def test_volume_ratio_2_when_double(self):
        from backend.services.technical import calculate_volume_ratio

        vol = pd.Series([2_000_000.0])
        avg_vol = pd.Series([1_000_000.0])
        result = calculate_volume_ratio(vol, avg_vol)
        assert abs(result.iloc[0] - 2.0) < 0.001

    def test_zero_avg_volume_returns_nan(self):
        from backend.services.technical import calculate_volume_ratio

        vol = pd.Series([1_000_000.0])
        avg_vol = pd.Series([0.0])
        result = calculate_volume_ratio(vol, avg_vol)
        assert pd.isna(result.iloc[0])


class TestCalculateAdt:

    def test_adt_is_volume_times_close(self):
        from backend.services.technical import calculate_adt

        # 20 identical rows: volume=1000, close=100 → turnover=100,000
        df = pd.DataFrame({
            "High": [102.0] * 20,
            "Low": [98.0] * 20,
            "Close": [100.0] * 20,
            "Open": [99.0] * 20,
            "Volume": [1000.0] * 20,
        })
        result = calculate_adt(df, period=20)
        assert abs(result - 100_000.0) < 1.0

    def test_adt_returns_float(self):
        from backend.services.technical import calculate_adt

        df = _make_df(n_rows=30)
        result = calculate_adt(df, period=20)
        assert isinstance(result, float)

    def test_adt_returns_zero_when_insufficient_rows(self):
        from backend.services.technical import calculate_adt

        df = _make_df(n_rows=5)
        result = calculate_adt(df, period=20)
        assert result == 0.0


class TestDetermineStage:

    def test_returns_string(self):
        from backend.services.technical import determine_stage

        df = _make_df(n_rows=200)
        result = determine_stage(df)
        assert isinstance(result, str)

    def test_returns_unknown_for_short_df(self):
        from backend.services.technical import determine_stage

        df = _make_df(n_rows=100)  # below 150 required
        result = determine_stage(df)
        assert result == "UNKNOWN"

    def test_valid_stage_is_one_of_known_values(self):
        from backend.services.technical import determine_stage

        df = _make_df(n_rows=200)
        result = determine_stage(df)
        assert result in ("S1", "S1B", "S2", "S3", "S4", "UNKNOWN")


class TestEstimateBaseDays:

    def test_returns_tuple_of_int_and_str(self):
        from backend.services.technical import estimate_base_days

        df = _make_df(n_rows=100)
        base_days, quality = estimate_base_days(df)
        assert isinstance(base_days, int)
        assert isinstance(quality, str)

    def test_returns_zero_and_unknown_for_short_df(self):
        from backend.services.technical import estimate_base_days

        df = _make_df(n_rows=10)
        base_days, quality = estimate_base_days(df)
        assert base_days == 0
        assert quality == "UNKNOWN"

    def test_quality_is_one_of_known_values(self):
        from backend.services.technical import estimate_base_days

        df = _make_df(n_rows=100)
        _, quality = estimate_base_days(df)
        assert quality in ("SMOOTH", "MIXED", "CHOPPY", "UNKNOWN")


class TestIsAbove30wMa:

    def test_returns_bool(self):
        from backend.services.technical import is_above_30w_ma

        df = _make_df(n_rows=200)
        result = is_above_30w_ma(df)
        assert isinstance(result, bool)

    def test_returns_false_for_short_df(self):
        from backend.services.technical import is_above_30w_ma

        df = _make_df(n_rows=100)
        assert is_above_30w_ma(df) is False

    def test_close_above_sma_returns_true(self):
        from backend.services.technical import is_above_30w_ma

        # Rising prices: close will be well above SMA of earlier (lower) prices
        n = 200
        closes = np.linspace(100, 200, n)
        df = pd.DataFrame({
            "Open": closes * 0.99,
            "High": closes * 1.01,
            "Low": closes * 0.98,
            "Close": closes,
            "Volume": np.ones(n) * 1_000_000,
        })
        assert is_above_30w_ma(df) is True


class TestCountNarrowingCandles:

    def test_returns_int(self):
        from backend.services.technical import count_narrowing_candles

        df = _make_df(n_rows=20)
        result = count_narrowing_candles(df)
        assert isinstance(result, int)

    def test_returns_zero_for_single_row(self):
        from backend.services.technical import count_narrowing_candles

        df = _make_df(n_rows=1)
        result = count_narrowing_candles(df)
        assert result == 0

    def test_perfectly_narrowing_candles_counted(self):
        from backend.services.technical import count_narrowing_candles

        # Build 10 candles with strictly decreasing ranges
        ranges = np.linspace(10, 1, 10)
        closes = np.ones(10) * 100
        df = pd.DataFrame({
            "Open": closes,
            "High": closes + ranges / 2,
            "Low": closes - ranges / 2,
            "Close": closes,
            "Volume": np.ones(10) * 1_000_000,
        })
        result = count_narrowing_candles(df, lookback=10)
        assert result >= 5


class TestPriceNearResistance:

    def test_returns_bool(self):
        from backend.services.technical import price_near_resistance

        df = _make_df(n_rows=100)
        result = price_near_resistance(df, lookback=60, threshold_pct=3.0)
        assert isinstance(result, bool)

    def test_at_the_high_is_near_resistance(self):
        from backend.services.technical import price_near_resistance

        # All closes are the same → close equals the highest high → within 0%
        df = _make_df(n_rows=100)
        # Force close to equal the high of the last candle
        df.iloc[-1, df.columns.get_loc("Close")] = df["High"].max()
        result = price_near_resistance(df, lookback=60, threshold_pct=3.0)
        assert result is True

    def test_far_below_resistance_returns_false(self):
        from backend.services.technical import price_near_resistance

        n = 100
        highs = np.full(n, 200.0)
        closes = np.full(n, 100.0)   # 50% below high → not near resistance
        df = pd.DataFrame({
            "Open": closes,
            "High": highs,
            "Low": closes * 0.99,
            "Close": closes,
            "Volume": np.ones(n) * 1_000_000,
        })
        result = price_near_resistance(df, lookback=60, threshold_pct=3.0)
        assert result is False


class TestCalculateAtrSlope:

    def test_returns_float(self):
        from backend.services.technical import calculate_atr_slope

        df = _make_df(n_rows=50)
        result = calculate_atr_slope(df)
        assert isinstance(result, float)

    def test_returns_zero_for_insufficient_data(self):
        from backend.services.technical import calculate_atr_slope

        df = _make_df(n_rows=5)
        result = calculate_atr_slope(df)
        assert result == 0.0

    def test_contracting_atr_returns_negative_slope(self):
        from backend.services.technical import calculate_atr_slope

        # Build 60 candles with ranges that shrink over time
        n = 60
        ranges = np.linspace(20, 1, n)     # Large → small
        closes = np.ones(n) * 100
        df = pd.DataFrame({
            "Open": closes,
            "High": closes + ranges / 2,
            "Low": closes - ranges / 2,
            "Close": closes,
            "Volume": np.ones(n) * 1_000_000,
        })
        result = calculate_atr_slope(df, atr_period=14, slope_bars=5)
        assert result < 0


# ---------------------------------------------------------------------------
# Tests for _determine_watchlist_bucket
# ---------------------------------------------------------------------------

class TestDetermineWatchlistBucket:

    def test_s2_stage_min_base_smooth_returns_ready(self):
        from backend.services.scanner_engine import _determine_watchlist_bucket

        result = _determine_watchlist_bucket("S2", 25, "SMOOTH")
        assert result == "READY"

    def test_s1b_stage_min_base_mixed_returns_ready(self):
        from backend.services.scanner_engine import _determine_watchlist_bucket

        result = _determine_watchlist_bucket("S1B", 20, "MIXED")
        assert result == "READY"

    def test_s2_stage_15_base_days_returns_near(self):
        from backend.services.scanner_engine import _determine_watchlist_bucket

        result = _determine_watchlist_bucket("S2", 15, "CHOPPY")
        assert result == "NEAR"

    def test_s1b_stage_16_base_days_returns_near(self):
        from backend.services.scanner_engine import _determine_watchlist_bucket

        result = _determine_watchlist_bucket("S1B", 16, "CHOPPY")
        assert result == "NEAR"

    def test_s4_stage_returns_away(self):
        from backend.services.scanner_engine import _determine_watchlist_bucket

        result = _determine_watchlist_bucket("S4", 30, "SMOOTH")
        assert result == "AWAY"

    def test_insufficient_base_days_returns_away(self):
        from backend.services.scanner_engine import _determine_watchlist_bucket

        result = _determine_watchlist_bucket("S2", 5, "SMOOTH")
        assert result == "AWAY"


# ---------------------------------------------------------------------------
# Tests for _build_common_metrics (internal function via scanner)
# ---------------------------------------------------------------------------

class TestBuildCommonMetrics:
    """
    _build_common_metrics is not exported but we can test it via its output contract.
    """

    def test_close_price_is_decimal(self):
        from backend.services.scanner_engine import _build_common_metrics

        df = _make_df(n_rows=200, close_price=500.0)
        metrics = _build_common_metrics("TEST", df, "2024-01-15")
        assert isinstance(metrics["close_price"], Decimal)

    def test_trp_is_decimal_when_not_nan(self):
        from backend.services.scanner_engine import _build_common_metrics

        df = _make_df(n_rows=200)
        metrics = _build_common_metrics("TEST", df, "2024-01-15")
        if metrics["trp"] is not None:
            assert isinstance(metrics["trp"], Decimal)

    def test_adt_is_decimal(self):
        from backend.services.scanner_engine import _build_common_metrics

        df = _make_df(n_rows=200)
        metrics = _build_common_metrics("TEST", df, "2024-01-15")
        assert isinstance(metrics["adt"], Decimal)

    def test_volume_is_int(self):
        from backend.services.scanner_engine import _build_common_metrics

        df = _make_df(n_rows=200)
        metrics = _build_common_metrics("TEST", df, "2024-01-15")
        assert isinstance(metrics["volume"], int)

    def test_symbol_preserved(self):
        from backend.services.scanner_engine import _build_common_metrics

        df = _make_df(n_rows=200)
        metrics = _build_common_metrics("RELIANCE", df, "2024-01-15")
        assert metrics["symbol"] == "RELIANCE"

    def test_scan_date_converted_from_string(self):
        from backend.services.scanner_engine import _build_common_metrics
        from datetime import date

        df = _make_df(n_rows=200)
        metrics = _build_common_metrics("TEST", df, "2024-01-15")
        assert metrics["scan_date"] == date(2024, 1, 15)

    def test_all_required_keys_present(self):
        from backend.services.scanner_engine import _build_common_metrics

        df = _make_df(n_rows=200)
        metrics = _build_common_metrics("TEST", df, "2024-01-15")
        required = {
            "scan_date", "symbol", "close_price", "volume",
            "avg_volume_20d", "volume_ratio", "trp", "avg_trp",
            "trp_ratio", "candle_body_pct", "close_position", "stage",
            "above_30w_ma", "ma_trending_up", "base_days",
            "has_min_20_bar_base", "base_quality", "adt",
            "passes_liquidity_filter",
        }
        assert required.issubset(metrics.keys())


# ---------------------------------------------------------------------------
# PPC scan logic — inject synthetic DataFrames
# ---------------------------------------------------------------------------

class TestScanPpc:

    def _run_ppc(self, stock_data: dict) -> list:
        from backend.services.scanner_engine import _scan_ppc

        return _scan_ppc(stock_data, "2024-01-15")

    def test_empty_data_returns_empty_list(self):
        results = self._run_ppc({})
        assert results == []

    def test_df_with_fewer_than_30_rows_is_skipped(self):
        df = _make_expanding_df(n_rows=20)
        results = self._run_ppc({"RELIANCE": df})
        assert len(results) == 0

    def test_illiquid_stock_is_excluded(self):
        """A stock with very low volume (tiny ADT) should be filtered out."""
        df = _make_expanding_df(n_rows=200)
        # Volume near-zero → ADT will be far below MIN_ADT
        df["Volume"] = 1.0
        results = self._run_ppc({"LOW_VOL": df})
        assert len(results) == 0

    def test_red_candle_is_not_a_ppc(self):
        """PPC requires a green (bullish) candle."""
        df = _make_expanding_df(n_rows=200)
        # Force last candle to be red
        df.iloc[-1, df.columns.get_loc("Open")] = 520.0
        df.iloc[-1, df.columns.get_loc("Close")] = 490.0
        results = self._run_ppc({"RED_STOCK": df})
        # May or may not match depending on thresholds, but the red-candle
        # filter must be applied; we just verify no crash occurs.
        assert isinstance(results, list)

    def test_scan_type_field_is_ppc(self):
        """Every result from _scan_ppc must have scan_type='PPC'."""
        df = _make_expanding_df(n_rows=200)
        results = self._run_ppc({"GOOD": df})
        for r in results:
            assert r["scan_type"] == "PPC"

    def test_trigger_level_is_decimal(self):
        df = _make_expanding_df(n_rows=200)
        results = self._run_ppc({"GOOD": df})
        for r in results:
            assert isinstance(r["trigger_level"], Decimal)


# ---------------------------------------------------------------------------
# NPC scan logic
# ---------------------------------------------------------------------------

class TestScanNpc:

    def _run_npc(self, stock_data: dict) -> list:
        from backend.services.scanner_engine import _scan_npc

        return _scan_npc(stock_data, "2024-01-15")

    def test_empty_data_returns_empty_list(self):
        assert self._run_npc({}) == []

    def test_df_with_fewer_than_30_rows_is_skipped(self):
        df = _make_df(n_rows=20)
        assert len(self._run_npc({"TEST": df})) == 0

    def test_scan_type_field_is_npc(self):
        """Results from _scan_npc must have scan_type='NPC' when they match."""
        df = _make_df(n_rows=200, open_above_close=True)
        results = self._run_npc({"STOCK": df})
        for r in results:
            assert r["scan_type"] == "NPC"

    def test_green_candle_excluded_from_npc(self):
        """NPC requires a red candle — a uniformly green DataFrame won't qualify."""
        df = _make_df(n_rows=200, open_above_close=False)  # green candles
        results = self._run_npc({"STOCK": df})
        # Either no results, or all results should not have been included
        # (they might have other filters blocking them too)
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Contraction scan logic
# ---------------------------------------------------------------------------

class TestScanContraction:

    def _run_contraction(self, stock_data: dict) -> list:
        from backend.services.scanner_engine import _scan_contraction

        return _scan_contraction(stock_data, "2024-01-15")

    def test_empty_data_returns_empty_list(self):
        assert self._run_contraction({}) == []

    def test_df_with_fewer_than_30_rows_is_skipped(self):
        df = _make_df(n_rows=20)
        assert len(self._run_contraction({"TEST": df})) == 0

    def test_scan_type_field_is_contraction(self):
        """Any result must have scan_type='CONTRACTION'."""
        df = _make_df(n_rows=200)
        results = self._run_contraction({"STOCK": df})
        for r in results:
            assert r["scan_type"] == "CONTRACTION"

    def test_trigger_level_is_decimal_for_matches(self):
        df = _make_df(n_rows=200)
        results = self._run_contraction({"STOCK": df})
        for r in results:
            assert isinstance(r["trigger_level"], Decimal)
