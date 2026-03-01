"""
Pure technical analysis functions for the Champion Trader scanner.
All functions operate on pandas DataFrames with OHLCV columns.
"""

import numpy as np
import pandas as pd


def calculate_trp(df: pd.DataFrame) -> pd.Series:
    """
    True Range Percentage — measures candle range as % of close.
    TRP = (High - Low) / Close × 100
    """
    return (df["High"] - df["Low"]) / df["Close"] * 100


def calculate_avg_trp(trp: pd.Series, period: int = 20) -> pd.Series:
    """Rolling average of TRP over given period."""
    return trp.rolling(window=period, min_periods=period).mean()


def calculate_trp_ratio(trp: pd.Series, avg_trp: pd.Series) -> pd.Series:
    """Ratio of current TRP to its average — measures range expansion."""
    return trp / avg_trp.replace(0, np.nan)


def calculate_close_position(df: pd.DataFrame) -> pd.Series:
    """
    Where the close sits within the candle range.
    1.0 = closed at high, 0.0 = closed at low.
    """
    candle_range = df["High"] - df["Low"]
    return (df["Close"] - df["Low"]) / candle_range.replace(0, np.nan)


def calculate_candle_body_pct(df: pd.DataFrame) -> pd.Series:
    """
    Body size as percentage of total candle range.
    High body% = strong conviction candle.
    """
    candle_range = df["High"] - df["Low"]
    body = (df["Close"] - df["Open"]).abs()
    return body / candle_range.replace(0, np.nan)


def calculate_avg_volume(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Rolling average volume."""
    return df["Volume"].rolling(window=period, min_periods=period).mean()


def calculate_volume_ratio(volume: pd.Series, avg_volume: pd.Series) -> pd.Series:
    """Current volume divided by average — measures participation spike."""
    return volume / avg_volume.replace(0, np.nan)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range — Wilder's smoothed ATR.
    Uses the standard true range definition.
    """
    high_low = df["High"] - df["Low"]
    high_prev_close = (df["High"] - df["Close"].shift(1)).abs()
    low_prev_close = (df["Low"] - df["Close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def calculate_adt(df: pd.DataFrame, period: int = 20) -> float:
    """
    Average Daily Turnover — avg(Volume × Close) over period.
    Returns the latest value as a scalar.
    """
    turnover = df["Volume"] * df["Close"]
    avg_turnover = turnover.rolling(window=period, min_periods=period).mean()
    latest = avg_turnover.iloc[-1]
    if pd.isna(latest):
        return 0.0
    return float(latest)


def determine_stage(df: pd.DataFrame) -> str:
    """
    Determine Weinstein stage using 150-day SMA as proxy for 30-week MA.

    S1  = Basing — price near and oscillating around SMA, SMA flat
    S1B = Late basing — price starting to lift above SMA, SMA flattening/turning up
    S2  = Advancing — price above rising SMA
    S3  = Topping — price near SMA, SMA flattening after advance
    S4  = Declining — price below falling SMA
    """
    if len(df) < 150:
        return "UNKNOWN"

    sma_150 = df["Close"].rolling(window=150).mean()
    current_close = df["Close"].iloc[-1]
    current_sma = sma_150.iloc[-1]
    sma_20_ago = sma_150.iloc[-20] if len(sma_150) >= 20 else sma_150.iloc[0]

    if pd.isna(current_sma) or pd.isna(sma_20_ago):
        return "UNKNOWN"

    # SMA slope over last 20 bars
    sma_slope_pct = (current_sma - sma_20_ago) / sma_20_ago * 100
    price_vs_sma_pct = (current_close - current_sma) / current_sma * 100

    # S4: Price well below declining SMA
    if price_vs_sma_pct < -5 and sma_slope_pct < -0.5:
        return "S4"

    # S2: Price above rising SMA
    if price_vs_sma_pct > 3 and sma_slope_pct > 0.5:
        return "S2"

    # S1B: Price near or slightly above SMA, SMA flattening or starting to rise
    if -3 <= price_vs_sma_pct <= 8 and -0.5 <= sma_slope_pct <= 1.5:
        # Check if price is above SMA — late basing, getting ready
        if price_vs_sma_pct > 0:
            return "S1B"
        return "S1"

    # S3: Price near SMA after a run-up, SMA still slightly positive but flattening
    if -5 <= price_vs_sma_pct <= 3 and -1.0 <= sma_slope_pct <= 0.5:
        return "S3"

    # S1: General basing
    if -5 <= price_vs_sma_pct <= 5 and abs(sma_slope_pct) < 1.0:
        return "S1"

    # Default fallback based on price vs SMA
    if price_vs_sma_pct > 0:
        return "S2"
    return "S4"


def estimate_base_days(df: pd.DataFrame) -> tuple[int, str]:
    """
    Estimate how many days the stock has been in a base formation,
    and assess base quality.

    Returns: (base_days, quality) where quality is SMOOTH, MIXED, or CHOPPY.

    A base = price trading in a range near support/resistance with declining volatility.
    We look backwards from the latest bar for the period where price stayed within
    a bounded range.
    """
    if len(df) < 30:
        return (0, "UNKNOWN")

    closes = df["Close"].values
    highs = df["High"].values
    lows = df["Low"].values
    current_close = closes[-1]

    # Define base range: +/-15% of the recent pivot high
    recent_high = float(np.max(highs[-60:])) if len(highs) >= 60 else float(np.max(highs))
    upper_bound = recent_high * 1.02  # Allow small overshoot
    lower_bound = recent_high * 0.85  # Base within 15% of high

    # Walk backwards counting days within the range
    base_days = 0
    for i in range(len(closes) - 1, -1, -1):
        if lower_bound <= closes[i] <= upper_bound:
            base_days += 1
        else:
            break

    if base_days < 10:
        return (base_days, "UNKNOWN")

    # Assess quality by measuring daily range volatility within the base
    base_slice = df.iloc[-base_days:]
    daily_ranges = (base_slice["High"] - base_slice["Low"]) / base_slice["Close"]
    range_std = daily_ranges.std()

    if range_std < 0.015:
        quality = "SMOOTH"
    elif range_std < 0.025:
        quality = "MIXED"
    else:
        quality = "CHOPPY"

    return (base_days, quality)


def is_above_30w_ma(df: pd.DataFrame) -> bool:
    """Check if current close is above the 150-day SMA (30-week proxy)."""
    if len(df) < 150:
        return False
    sma_150 = df["Close"].rolling(window=150).mean().iloc[-1]
    if pd.isna(sma_150):
        return False
    return bool(df["Close"].iloc[-1] > sma_150)


def is_ma_trending_up(df: pd.DataFrame) -> bool:
    """Check if the 150-day SMA is trending upward over the last 20 bars."""
    if len(df) < 170:
        return False
    sma_150 = df["Close"].rolling(window=150).mean()
    current_sma = sma_150.iloc[-1]
    sma_20_ago = sma_150.iloc[-20]
    if pd.isna(current_sma) or pd.isna(sma_20_ago):
        return False
    return bool(current_sma > sma_20_ago)


def calculate_atr_slope(df: pd.DataFrame, atr_period: int = 14, slope_bars: int = 5) -> float:
    """
    Calculate the slope of ATR over the last N bars.
    Negative slope = contracting volatility (good for contraction scan).
    Returns slope as a ratio: (latest ATR - ATR N bars ago) / ATR N bars ago
    """
    atr = calculate_atr(df, atr_period)
    if len(atr) < slope_bars + atr_period:
        return 0.0
    latest = atr.iloc[-1]
    earlier = atr.iloc[-(slope_bars + 1)]
    if pd.isna(latest) or pd.isna(earlier) or earlier == 0:
        return 0.0
    return float((latest - earlier) / earlier)


def count_narrowing_candles(df: pd.DataFrame, lookback: int = 10, tolerance: float = 0.05) -> int:
    """
    Count consecutive narrowing-range candles from the latest bar going backwards.
    A candle is 'narrowing' if its range <= previous range × (1 + tolerance).
    """
    if len(df) < 2:
        return 0

    ranges = (df["High"] - df["Low"]).values
    recent = ranges[-lookback:] if len(ranges) >= lookback else ranges

    count = 0
    for i in range(len(recent) - 1, 0, -1):
        if recent[i - 1] == 0:
            break
        if recent[i] <= recent[i - 1] * (1 + tolerance):
            count += 1
        else:
            break
    return count


def price_near_resistance(df: pd.DataFrame, lookback: int = 60, threshold_pct: float = 3.0) -> bool:
    """
    Check if current price is within threshold_pct% of the highest high
    over the lookback period. Near resistance = potential breakout.
    """
    if len(df) < lookback:
        lookback = len(df)
    highest_high = df["High"].iloc[-lookback:].max()
    current_close = df["Close"].iloc[-1]
    if pd.isna(highest_high) or highest_high == 0:
        return False
    distance_pct = (highest_high - current_close) / highest_high * 100
    return bool(distance_pct <= threshold_pct)
