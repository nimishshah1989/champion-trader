"""Per-stock-relative candle features (A3a) — first slice of the signal engine.

Computes, for the latest bar, the volatility/participation features that
PPC/NPC/contraction are built from — all RELATIVE TO THE STOCK'S OWN recent
history (ratio + z-score), never absolute constants. This is the upgrade that
replaces the legacy hard-coded ``1.5x`` thresholds. Operates on the leakage-safe
Bar list from kite_data.

Statistical features are floats (they are not money); Bar prices stay Decimal.

NOTE: delivery-% (the NSE institutional-accumulation anomaly) is NOT in Kite
historical candles — it needs NSE bhavcopy ingestion (planned as A2b). Until
then, features are OHLCV-derived.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, pstdev

from backend.engine.kite_data import Bar


@dataclass(frozen=True)
class CandleFeatures:
    trp: float             # (high-low)/close*100 of the latest bar
    avg_trp: float         # mean TRP over the prior `lookback` bars
    trp_ratio: float       # latest TRP / avg TRP  (range expansion, per-stock)
    trp_z: float           # z-score of latest TRP vs prior bars
    close_position: float  # (close-low)/(high-low); 1.0 = closed at the high
    volume_ratio: float    # latest volume / avg volume  (participation, per-stock)
    volume_z: float        # z-score of latest volume vs prior bars
    is_green: bool


def _trp(b: Bar) -> float:
    c = float(b.close)
    return (float(b.high - b.low) / c * 100.0) if c else 0.0


def compute_latest_features(bars: list[Bar], lookback: int = 20) -> CandleFeatures:
    """Features for ``bars[-1]`` measured against the prior ``lookback`` bars."""
    if len(bars) < lookback + 1:
        raise ValueError(f"need >= {lookback + 1} bars, got {len(bars)}")

    latest = bars[-1]
    prior = bars[-(lookback + 1):-1]   # the `lookback` bars before the latest

    trps_prior = [_trp(b) for b in prior]
    vols_prior = [float(b.volume) for b in prior]
    trp = _trp(latest)
    vol = float(latest.volume)

    avg_trp = fmean(trps_prior)
    avg_vol = fmean(vols_prior)
    trp_sd = pstdev(trps_prior)
    vol_sd = pstdev(vols_prior)

    rng = float(latest.high - latest.low)
    close_pos = (float(latest.close - latest.low) / rng) if rng else 0.0

    return CandleFeatures(
        trp=trp,
        avg_trp=avg_trp,
        trp_ratio=(trp / avg_trp) if avg_trp else 0.0,
        trp_z=((trp - avg_trp) / trp_sd) if trp_sd else 0.0,
        close_position=close_pos,
        volume_ratio=(vol / avg_vol) if avg_vol else 0.0,
        volume_z=((vol - avg_vol) / vol_sd) if vol_sd else 0.0,
        is_green=latest.close > latest.open,
    )
