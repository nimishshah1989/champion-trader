"""Base-structure analysis (A3d) — the Minervini/O'Neil base the legacy scanner lacked.

Locates the most-recent pivot high and measures the consolidation that followed:
  * base_bars        — how long it has been basing (length);
  * depth_pct        — pivot-to-trough %, with a deep-base failure ceiling;
  * prior_advance_pct — the rise into the base (a base is only a *continuation*
                        pattern if there was an advance to continue).

A first cut: the VCP "progressively-shallower contraction count" refinement is
planned as A3d-2. Thresholds here are defaults, to be calibrated in Phase B.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from backend.engine.kite_data import Bar


@dataclass(frozen=True)
class BaseResult:
    is_valid_base: bool
    base_bars: int
    depth_pct: float
    prior_advance_pct: float
    pivot_high: Decimal
    base_low: Decimal


def analyze_base(
    bars: list[Bar],
    *,
    lookback: int = 60,
    advance_lookback: int = 30,
    min_base_bars: int = 20,
    min_depth_pct: float = 8.0,
    max_depth_pct: float = 35.0,
    min_prior_advance_pct: float = 20.0,
) -> BaseResult:
    if len(bars) < min_base_bars + 2:
        return BaseResult(False, 0, 0.0, 0.0, Decimal("0"), Decimal("0"))

    window = bars[-lookback:] if len(bars) >= lookback else bars
    offset = len(bars) - len(window)

    # Most-recent pivot high (last occurrence of the max high in the window).
    pivot_local = 0
    for i, b in enumerate(window):
        if b.high >= window[pivot_local].high:
            pivot_local = i
    pivot_idx = offset + pivot_local
    pivot_high = bars[pivot_idx].high

    base_bars = (len(bars) - 1) - pivot_idx
    base_low = min(b.low for b in bars[pivot_idx:])
    depth_pct = float((pivot_high - base_low) / pivot_high * 100) if pivot_high else 0.0

    pre = bars[max(0, pivot_idx - advance_lookback):pivot_idx]
    if pre:
        advance_low = min(b.low for b in pre)
        prior_advance_pct = (
            float((pivot_high - advance_low) / advance_low * 100) if advance_low else 0.0
        )
    else:
        prior_advance_pct = 0.0

    is_valid = (
        base_bars >= min_base_bars
        and min_depth_pct <= depth_pct <= max_depth_pct
        and prior_advance_pct >= min_prior_advance_pct
    )
    return BaseResult(is_valid, base_bars, depth_pct, prior_advance_pct, pivot_high, base_low)
