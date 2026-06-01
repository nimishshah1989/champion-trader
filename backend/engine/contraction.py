"""Volatility-contraction detector (A3c) — the coil before the breakout.

Fixes two legacy bugs:
  * the ATR "slope" was a 2-point endpoint ratio  ->  now a least-squares slope;
  * the "narrowing" counter used an inverted +tolerance that counted WIDER bars
    as narrowing  ->  now strict (a bar's range must be <= the prior bar's).

A contraction = ATR declining (regression slope < 0) AND >= N consecutive
non-widening bars AND price coiling near resistance. trigger_level = the high to
break (max high of the last few bars).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import fmean

from backend.engine.kite_data import Bar


@dataclass(frozen=True)
class ContractionResult:
    is_contraction: bool
    atr_slope_pct: float
    narrowing_count: int
    near_resistance: bool
    trigger_level: Decimal


def _linreg_slope(ys: list[float]) -> float:
    n = len(ys)
    if n < 2:
        return 0.0
    xs = range(n)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    return (n * sxy - sx * sy) / denom if denom else 0.0


def _consecutive_narrowing(ranges: list[float]) -> int:
    """Count consecutive non-widening bars from the latest backward (strict)."""
    count = 0
    for k in range(len(ranges) - 1, 0, -1):
        if ranges[k] <= ranges[k - 1]:
            count += 1
        else:
            break
    return count


def _atr_series(bars: list[Bar], period: int = 14) -> list[float]:
    trs: list[float] = []
    for i in range(1, len(bars)):
        h, l, pc = float(bars[i].high), float(bars[i].low), float(bars[i - 1].close)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return [fmean(trs[i - period + 1:i + 1]) for i in range(period - 1, len(trs))]


def detect_contraction(
    bars: list[Bar],
    *,
    atr_period: int = 14,
    slope_lookback: int = 10,
    min_narrowing: int = 3,
    narrowing_window: int = 10,
    resistance_lookback: int = 60,
    resistance_pct: float = 3.0,
    trigger_lookback: int = 5,
) -> ContractionResult:
    if len(bars) < atr_period + slope_lookback + 1:
        return ContractionResult(False, 0.0, 0, False, Decimal("0"))

    atr = _atr_series(bars, atr_period)
    recent = atr[-slope_lookback:]
    mean_atr = fmean(recent)
    slope_pct = (_linreg_slope(recent) / mean_atr * 100) if mean_atr else 0.0

    ranges = [float(b.high - b.low) for b in bars[-narrowing_window:]]
    narrowing = _consecutive_narrowing(ranges)

    lb = min(resistance_lookback, len(bars))
    hi = max(float(b.high) for b in bars[-lb:])
    close = float(bars[-1].close)
    near = ((hi - close) / hi * 100 <= resistance_pct) if hi else False

    trigger = max(b.high for b in bars[-trigger_lookback:])
    is_c = slope_pct < 0 and narrowing >= min_narrowing and near
    return ContractionResult(is_c, slope_pct, narrowing, near, trigger)
