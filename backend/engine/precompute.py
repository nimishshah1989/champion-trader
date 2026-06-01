"""Vectorized feature engine (A5d) — compute every indicator series ONCE per
symbol with pandas/numpy (rolling ops in C), so a backtest is O(n) instead of
re-deriving indicators per bar (O(n^2)).

Every column reproduces the pure-Python detector semantics exactly (proven by a
bar-for-bar differential test). All ops are backward-rolling => no look-ahead.
Statistical features are float64 (not money); fills/costs/R stay Decimal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.engine.contraction import _linreg_slope
from backend.engine.kite_data import Bar


def _frame(bars: list[Bar]) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [b.date for b in bars],
        "open": [float(b.open) for b in bars],
        "high": [float(b.high) for b in bars],
        "low": [float(b.low) for b in bars],
        "close": [float(b.close) for b in bars],
        "volume": [float(b.volume) for b in bars],
        "delivery_pct": [b.delivery_pct for b in bars],
    })


def precompute_features(
    bars: list[Bar],
    *,
    trp_lookback: int = 20,
    sma_window: int = 150,
    slope_lookback: int = 20,
    flat_eps: float = 0.5,
    hh_recent: int = 10,
    hh_prior: int = 20,
    atr_period: int = 14,
    atr_slope_lookback: int = 10,
    compression_lookback: int = 60,
    max_compression_pct: float = 0.35,
    resistance_lookback: int = 60,
    resistance_pct: float = 3.0,
    trigger_lookback: int = 5,
) -> pd.DataFrame:
    df = _frame(bars)
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]
    rng = h - l

    with np.errstate(divide="ignore", invalid="ignore"):
        # --- candle features (avg/std use the PRIOR `lookback` bars => shift(1)) ---
        trp = rng / c * 100
        avg_trp = trp.rolling(trp_lookback).mean().shift(1)
        trp_sd = trp.rolling(trp_lookback).std(ddof=0).shift(1)
        df["trp"] = trp
        df["avg_trp"] = avg_trp
        df["trp_ratio"] = np.where(avg_trp.to_numpy() > 0, trp / avg_trp, 0.0)
        df["trp_z"] = np.where(trp_sd.to_numpy() > 0, (trp - avg_trp) / trp_sd, 0.0)
        df["close_position"] = np.where(rng.to_numpy() != 0, (c - l) / rng, 0.0)
        avg_vol = v.rolling(trp_lookback).mean().shift(1)
        vol_sd = v.rolling(trp_lookback).std(ddof=0).shift(1)
        df["volume_ratio"] = np.where(avg_vol.to_numpy() > 0, v / avg_vol, 0.0)
        df["volume_z"] = np.where(vol_sd.to_numpy() > 0, (v - avg_vol) / vol_sd, 0.0)
        df["is_green"] = c > o

        # --- stage (Weinstein, mutually-exclusive bands) ---
        sma = c.rolling(sma_window).mean()
        sma_prev = sma.shift(slope_lookback)
        sma_slope = pd.Series(np.where(sma_prev.to_numpy() > 0, (sma - sma_prev) / sma_prev * 100, 0.0))
        price_vs = pd.Series(np.where(sma.to_numpy() > 0, (c - sma) / sma * 100, 0.0))
        hh = h.rolling(hh_recent).max() > h.rolling(hh_prior).max().shift(hh_recent)
        rising, falling = sma_slope > flat_eps, sma_slope < -flat_eps
        stage = np.select(
            [rising & (price_vs > 0) & hh, rising & (price_vs > 0) & (~hh), rising & (price_vs <= 0),
             falling & (price_vs < 0), falling & (price_vs >= 0)],
            ["S2", "S1B", "S1B", "S4", "S3"], default="S1",
        )
        stage = np.where(sma.isna().to_numpy() | sma_prev.isna().to_numpy(), "UNKNOWN", stage)
        df["sma_slope_pct"] = sma_slope.to_numpy()
        df["price_vs_sma_pct"] = price_vs.to_numpy()
        df["stage"] = stage

        # --- contraction (volatility compression) ---
        pc = c.shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()
        atr_mean = atr.rolling(atr_slope_lookback).mean()
        atr_slope = atr.rolling(atr_slope_lookback).apply(_linreg_slope, raw=True)
        atr_slope_pct = pd.Series(np.where(atr_mean.to_numpy() > 0, atr_slope / atr_mean * 100, 0.0))
        atr_pct = atr.rolling(compression_lookback).apply(lambda a: float((a <= a[-1]).mean()), raw=True)
        maxhigh = h.rolling(resistance_lookback).max()
        near = pd.Series(np.where(maxhigh.to_numpy() > 0, (maxhigh - c) / maxhigh * 100 <= resistance_pct, False))
        df["atr"] = atr
        df["atr_slope_pct"] = atr_slope_pct.to_numpy()
        df["atr_percentile"] = atr_pct
        df["near_resistance"] = near.to_numpy()
        df["is_contraction"] = (
            (atr_pct.fillna(1.0) <= max_compression_pct).to_numpy()
            & (atr_slope_pct <= 0).to_numpy()
            & near.to_numpy()
        )
        df["trigger_level"] = h.rolling(trigger_lookback).max()

    return df
