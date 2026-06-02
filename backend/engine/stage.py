"""Weinstein stage classifier (A3b) — mutually-exclusive bands.

Fixes the legacy bug where overlapping, order-dependent bands could tag a
TOPPING stock (price above a rolling-over MA) as S1B/S2 — a buy bucket. Here the
(price-vs-MA, MA-slope) plane is fully partitioned, so every input maps to
exactly one stage. S2 additionally requires higher highs; S1B can require
breakout-volume confirmation (else it stays S1).

Tradeable (long) stages: S1B, S2. Avoid: S1 (basing), S3 (topping), S4 (down).
"""
from __future__ import annotations

from statistics import fmean

from backend.engine.kite_data import Bar

UNKNOWN = "UNKNOWN"


def _stage_from_signals(
    price_vs_sma_pct: float,
    sma_slope_pct: float,
    making_higher_highs: bool,
    breakout_volume_confirmed: bool = True,
    flat_eps: float = 0.5,
) -> str:
    """Map the (price-vs-MA, MA-slope, higher-highs) signals to exactly one stage."""
    if sma_slope_pct > flat_eps:                 # MA rising
        if price_vs_sma_pct > 0:
            stage = "S2" if making_higher_highs else "S1B"
        else:
            stage = "S1B"                        # price at/below but MA turning up
        if stage == "S1B" and not breakout_volume_confirmed:
            stage = "S1"                         # breakout needs volume, else basing
        return stage
    if sma_slope_pct < -flat_eps:                # MA falling
        return "S4" if price_vs_sma_pct < 0 else "S3"   # S3 = topping (above rolling-over MA)
    return "S1"                                  # MA flat: basing


def classify_stage(
    bars: list[Bar],
    *,
    sma_window: int = 150,
    slope_lookback: int = 20,
    flat_eps: float = 0.5,
    hh_recent: int = 10,
    hh_prior: int = 20,
    breakout_volume_confirmed: bool = True,
) -> str:
    if len(bars) < sma_window + slope_lookback or len(bars) < hh_recent + hh_prior:
        return UNKNOWN
    closes = [float(b.close) for b in bars]
    highs = [float(b.high) for b in bars]
    sma_now = fmean(closes[-sma_window:])
    sma_prev = fmean(closes[-(sma_window + slope_lookback):-slope_lookback])
    s = (sma_now - sma_prev) / sma_prev * 100 if sma_prev else 0.0
    p = (closes[-1] - sma_now) / sma_now * 100 if sma_now else 0.0
    hh = max(highs[-hh_recent:]) > max(highs[-(hh_recent + hh_prior):-hh_recent])
    return _stage_from_signals(p, s, hh, breakout_volume_confirmed, flat_eps)
