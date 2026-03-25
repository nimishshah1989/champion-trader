"""
Backtest strategy/signal detection logic.

Contains PPC detection helpers: stage analysis, base estimation,
and indicator pre-computation for the backtest engine.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def precompute_indicators(ohlcv: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """
    Pre-compute all PPC detection metrics as vectorized Series.
    Returns {symbol: {trp_ratio, close_pos, vol_ratio, is_green, adt, high, ...}}
    where each value is a dict keyed by date_str for O(1) lookups.
    """
    indicators: dict[str, dict] = {}

    for symbol, df in ohlcv.items():
        try:
            if len(df) < 30:
                continue

            # TRP and ratios
            trp = (df["High"] - df["Low"]) / df["Close"] * 100
            avg_trp = trp.rolling(window=20, min_periods=20).mean()
            trp_ratio = trp / avg_trp.replace(0, np.nan)

            # Close position
            candle_range = df["High"] - df["Low"]
            close_pos = (df["Close"] - df["Low"]) / candle_range.replace(0, np.nan)

            # Volume ratio
            avg_vol = df["Volume"].rolling(window=20, min_periods=20).mean()
            vol_ratio = df["Volume"] / avg_vol.replace(0, np.nan)

            # ADT (rolling)
            turnover = df["Volume"] * df["Close"]
            adt = turnover.rolling(window=20, min_periods=20).mean()

            # Is green candle
            is_green = df["Close"] > df["Open"]

            # 20 DMA for tighter trailing (3+ month override)
            dma20 = df["Close"].rolling(window=20, min_periods=20).mean()

            # 50 DMA for exit signals
            dma50 = df["Close"].rolling(window=50, min_periods=50).mean()

            # 150 DMA for stage analysis (pre-compute for efficiency)
            sma150 = df["Close"].rolling(window=150, min_periods=150).mean()

            # Build date-keyed lookups
            sym_data: dict = {
                "trp_ratio": {},
                "trp_pct": {},
                "close_pos": {},
                "vol_ratio": {},
                "is_green": {},
                "adt": {},
                "high": {},
                "low": {},
                "close": {},
                "open": {},
                "dma20": {},
                "dma50": {},
                "sma150": {},
                "sma150_20ago": {},
            }

            dates = df.index
            for i, idx in enumerate(dates):
                ds = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx.date())

                if pd.notna(trp_ratio.iloc[i]):
                    sym_data["trp_ratio"][ds] = float(trp_ratio.iloc[i])
                if pd.notna(trp.iloc[i]):
                    sym_data["trp_pct"][ds] = float(trp.iloc[i])
                if pd.notna(close_pos.iloc[i]):
                    sym_data["close_pos"][ds] = float(close_pos.iloc[i])
                if pd.notna(vol_ratio.iloc[i]):
                    sym_data["vol_ratio"][ds] = float(vol_ratio.iloc[i])
                sym_data["is_green"][ds] = bool(is_green.iloc[i])
                if pd.notna(adt.iloc[i]):
                    sym_data["adt"][ds] = float(adt.iloc[i])
                sym_data["high"][ds] = float(df["High"].iloc[i])
                sym_data["low"][ds] = float(df["Low"].iloc[i])
                sym_data["close"][ds] = float(df["Close"].iloc[i])
                sym_data["open"][ds] = float(df["Open"].iloc[i])
                if pd.notna(dma20.iloc[i]):
                    sym_data["dma20"][ds] = float(dma20.iloc[i])
                if pd.notna(dma50.iloc[i]):
                    sym_data["dma50"][ds] = float(dma50.iloc[i])
                if pd.notna(sma150.iloc[i]):
                    sym_data["sma150"][ds] = float(sma150.iloc[i])
                if i >= 20 and pd.notna(sma150.iloc[i - 20]):
                    sym_data["sma150_20ago"][ds] = float(sma150.iloc[i - 20])

            # Store raw DataFrame for stage/base analysis on PPC candidates
            sym_data["_df"] = df

            indicators[symbol] = sym_data

        except Exception as exc:
            logger.warning(f"Pre-compute failed for {symbol}: {exc}")

    return indicators


def check_stage_fast(ind: dict, day_str: str) -> str:
    """Fast stage determination using pre-computed SMA values."""
    current_close = ind["close"].get(day_str)
    current_sma = ind["sma150"].get(day_str)
    sma_20_ago = ind["sma150_20ago"].get(day_str)

    if current_close is None or current_sma is None or sma_20_ago is None:
        return "UNKNOWN"

    sma_slope_pct = (current_sma - sma_20_ago) / sma_20_ago * 100
    price_vs_sma_pct = (current_close - current_sma) / current_sma * 100

    if price_vs_sma_pct < -5 and sma_slope_pct < -0.5:
        return "S4"
    if price_vs_sma_pct > 3 and sma_slope_pct > 0.5:
        return "S2"
    if -3 <= price_vs_sma_pct <= 8 and -0.5 <= sma_slope_pct <= 1.5:
        if price_vs_sma_pct > 0:
            return "S1B"
        return "S1"
    if -5 <= price_vs_sma_pct <= 3 and -1.0 <= sma_slope_pct <= 0.5:
        return "S3"
    if -5 <= price_vs_sma_pct <= 5 and abs(sma_slope_pct) < 1.0:
        return "S1"
    if price_vs_sma_pct > 0:
        return "S2"
    return "S4"


def estimate_base_days_at(df: pd.DataFrame, day_idx: int) -> tuple[int, str]:
    """Estimate base days at a specific index in the DataFrame."""
    if day_idx < 30:
        return (0, "UNKNOWN")

    closes = df["Close"].values[:day_idx + 1]
    highs = df["High"].values[:day_idx + 1]

    lookback = min(60, len(highs))
    recent_high = float(np.max(highs[-lookback:]))
    upper_bound = recent_high * 1.02
    lower_bound = recent_high * 0.85

    base_days = 0
    for i in range(len(closes) - 1, -1, -1):
        if lower_bound <= closes[i] <= upper_bound:
            base_days += 1
        else:
            break

    if base_days < 10:
        return (base_days, "UNKNOWN")

    base_slice_h = df["High"].values[day_idx - base_days + 1:day_idx + 1]
    base_slice_l = df["Low"].values[day_idx - base_days + 1:day_idx + 1]
    base_slice_c = df["Close"].values[day_idx - base_days + 1:day_idx + 1]

    if len(base_slice_c) == 0:
        return (base_days, "UNKNOWN")

    daily_ranges = (base_slice_h - base_slice_l) / np.where(base_slice_c == 0, 1, base_slice_c)
    range_std = float(np.std(daily_ranges))

    if range_std < 0.015:
        quality = "SMOOTH"
    elif range_std < 0.025:
        quality = "MIXED"
    else:
        quality = "CHOPPY"

    return (base_days, quality)
