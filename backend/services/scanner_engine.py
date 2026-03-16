"""
Scanner engine — runs PPC, NPC, and Contraction scans on NIFTY 200 stocks.
Uses pre-downloaded OHLCV data (dict of symbol → DataFrame) to detect patterns.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

import pandas as pd

from backend.services.data_fetcher import fetch_all_stocks
from backend.intelligence.strategy import PARAMETERS
from backend.services.technical import (
    calculate_atr_slope,
    calculate_adt,
    calculate_avg_trp,
    calculate_avg_volume,
    calculate_candle_body_pct,
    calculate_close_position,
    calculate_trp,
    calculate_trp_ratio,
    calculate_volume_ratio,
    count_narrowing_candles,
    determine_stage,
    estimate_base_days,
    is_above_30w_ma,
    is_ma_trending_up,
    price_near_resistance,
)

logger = logging.getLogger(__name__)

# Minimum ADT filter: driven by strategy.py PARAMETERS
MIN_ADT = int(PARAMETERS["min_adt_crore"] * 1_00_00_000)


def _build_common_metrics(symbol: str, df: pd.DataFrame, scan_date: str) -> dict:
    """Compute metrics shared across all scan types for a single stock."""
    trp = calculate_trp(df)
    avg_trp = calculate_avg_trp(trp, period=20)
    trp_ratio = calculate_trp_ratio(trp, avg_trp)
    close_pos = calculate_close_position(df)
    body_pct = calculate_candle_body_pct(df)
    avg_vol = calculate_avg_volume(df, period=20)
    vol_ratio = calculate_volume_ratio(df["Volume"], avg_vol)
    adt = calculate_adt(df, period=20)
    stage = determine_stage(df)
    base_days, base_quality = estimate_base_days(df)
    above_ma = is_above_30w_ma(df)
    ma_up = is_ma_trending_up(df)

    # Convert scan_date string to date object for SQLAlchemy
    scan_date_obj = date.fromisoformat(scan_date) if isinstance(scan_date, str) else scan_date

    return {
        "scan_date": scan_date_obj,
        "symbol": symbol,
        "close_price": Decimal(str(round(float(df["Close"].iloc[-1]), 2))),
        "volume": int(df["Volume"].iloc[-1]),
        "avg_volume_20d": round(float(avg_vol.iloc[-1]), 0) if pd.notna(avg_vol.iloc[-1]) else None,
        "volume_ratio": round(float(vol_ratio.iloc[-1]), 2) if pd.notna(vol_ratio.iloc[-1]) else None,
        "trp": Decimal(str(round(float(trp.iloc[-1]), 2))) if pd.notna(trp.iloc[-1]) else None,
        "avg_trp": Decimal(str(round(float(avg_trp.iloc[-1]), 2))) if pd.notna(avg_trp.iloc[-1]) else None,
        "trp_ratio": round(float(trp_ratio.iloc[-1]), 2) if pd.notna(trp_ratio.iloc[-1]) else None,
        "candle_body_pct": round(float(body_pct.iloc[-1]), 2) if pd.notna(body_pct.iloc[-1]) else None,
        "close_position": round(float(close_pos.iloc[-1]), 2) if pd.notna(close_pos.iloc[-1]) else None,
        "stage": stage,
        "above_30w_ma": above_ma,
        "ma_trending_up": ma_up,
        "base_days": base_days,
        "has_min_20_bar_base": base_days >= PARAMETERS["min_base_days"],
        "base_quality": base_quality,
        "adt": Decimal(str(round(adt, 0))),
        "passes_liquidity_filter": adt >= MIN_ADT,
    }


def _determine_watchlist_bucket(stage: str, base_days: int, base_quality: str) -> str:
    """Suggest a watchlist bucket based on stage and base analysis."""
    if stage in ("S1B", "S2") and base_days >= PARAMETERS["min_base_days"] and base_quality in ("SMOOTH", "MIXED"):
        return "READY"
    if stage in ("S1B", "S2") and base_days >= 15:
        return "NEAR"
    return "AWAY"


def _scan_ppc(all_data: dict[str, pd.DataFrame], scan_date: str) -> list[dict]:
    """
    Positive Pivotal Candle scan.
    ALL 4 conditions must be met:
    1. TRP ratio >= 1.5 (range expansion)
    2. Close position >= 0.60 (bullish close in upper part)
    3. Volume ratio >= 1.5 (participation spike)
    4. Close > Open (green candle)
    """
    results = []

    for symbol, df in all_data.items():
        try:
            if len(df) < 30:
                continue

            metrics = _build_common_metrics(symbol, df, scan_date)

            # Skip illiquid stocks
            if not metrics["passes_liquidity_filter"]:
                continue

            # Core PPC conditions
            trp_ratio = metrics["trp_ratio"]
            close_pos = metrics["close_position"]
            vol_ratio = metrics["volume_ratio"]
            is_green = df["Close"].iloc[-1] > df["Open"].iloc[-1]

            if (
                trp_ratio is not None
                and close_pos is not None
                and vol_ratio is not None
                and trp_ratio >= PARAMETERS["ppc_trp_ratio_min"]
                and close_pos >= PARAMETERS["ppc_close_position_min"]
                and vol_ratio >= PARAMETERS["ppc_volume_ratio_min"]
                and is_green
            ):
                metrics["scan_type"] = "PPC"
                metrics["wuc_type"] = "MBB"  # Most common WUC for PPC
                metrics["trigger_level"] = Decimal(str(round(float(df["High"].iloc[-1]), 2)))
                metrics["watchlist_bucket"] = _determine_watchlist_bucket(
                    metrics["stage"], metrics["base_days"], metrics["base_quality"]
                )
                metrics["notes"] = (
                    f"PPC detected: TRP ratio {trp_ratio}x, "
                    f"Vol ratio {vol_ratio}x, Close pos {close_pos}"
                )
                results.append(metrics)

        except Exception as exc:
            logger.warning(f"PPC scan error for {symbol}: {exc}")

    logger.info(f"PPC scan complete: {len(results)} stocks matched")
    return results


def _scan_npc(all_data: dict[str, pd.DataFrame], scan_date: str) -> list[dict]:
    """
    Negative Pivotal Candle scan.
    ALL 4 conditions must be met:
    1. TRP ratio >= 1.5 (range expansion)
    2. Close position <= 0.40 (bearish close in lower part)
    3. Volume ratio >= 1.5 (participation spike)
    4. Close < Open (red candle)
    """
    results = []

    for symbol, df in all_data.items():
        try:
            if len(df) < 30:
                continue

            metrics = _build_common_metrics(symbol, df, scan_date)

            if not metrics["passes_liquidity_filter"]:
                continue

            trp_ratio = metrics["trp_ratio"]
            close_pos = metrics["close_position"]
            vol_ratio = metrics["volume_ratio"]
            is_red = df["Close"].iloc[-1] < df["Open"].iloc[-1]

            if (
                trp_ratio is not None
                and close_pos is not None
                and vol_ratio is not None
                and trp_ratio >= PARAMETERS["npc_trp_ratio_min"]
                and close_pos <= PARAMETERS["npc_close_position_max"]
                and vol_ratio >= PARAMETERS["npc_volume_ratio_min"]
                and is_red
            ):
                metrics["scan_type"] = "NPC"
                metrics["wuc_type"] = None
                metrics["trigger_level"] = Decimal(str(round(float(df["Low"].iloc[-1]), 2)))
                metrics["watchlist_bucket"] = _determine_watchlist_bucket(
                    metrics["stage"], metrics["base_days"], metrics["base_quality"]
                )
                metrics["notes"] = (
                    f"NPC detected: TRP ratio {trp_ratio}x, "
                    f"Vol ratio {vol_ratio}x, Close pos {close_pos}"
                )
                results.append(metrics)

        except Exception as exc:
            logger.warning(f"NPC scan error for {symbol}: {exc}")

    logger.info(f"NPC scan complete: {len(results)} stocks matched")
    return results


def _scan_contraction(all_data: dict[str, pd.DataFrame], scan_date: str) -> list[dict]:
    """
    Base contraction scan — volatility coiling before potential breakout.
    ALL 3 conditions must be met:
    1. ATR(14) slope negative over last 5 bars (declining volatility)
    2. 3+ narrowing-range candles (with 5% tolerance)
    3. Price within 3% of highest high over 60 bars (near resistance)
    """
    results = []

    for symbol, df in all_data.items():
        try:
            if len(df) < 30:
                continue

            metrics = _build_common_metrics(symbol, df, scan_date)

            if not metrics["passes_liquidity_filter"]:
                continue

            # Contraction conditions
            atr_slope = calculate_atr_slope(df, atr_period=14, slope_bars=5)
            narrowing_count = count_narrowing_candles(df, lookback=10, tolerance=0.05)
            near_resistance = price_near_resistance(df, lookback=60, threshold_pct=PARAMETERS["contraction_resistance_pct"])

            if atr_slope < 0 and narrowing_count >= PARAMETERS["contraction_narrowing_min"] and near_resistance:
                metrics["scan_type"] = "CONTRACTION"
                metrics["wuc_type"] = "BA"  # Breakout Anticipated
                # Trigger = highest high of the last 5 bars (breakout level)
                metrics["trigger_level"] = Decimal(str(round(float(df["High"].iloc[-5:].max()), 2)))
                metrics["watchlist_bucket"] = _determine_watchlist_bucket(
                    metrics["stage"], metrics["base_days"], metrics["base_quality"]
                )
                metrics["notes"] = (
                    f"Contraction detected: ATR slope {atr_slope:.3f}, "
                    f"{narrowing_count} narrowing candles, near resistance"
                )
                results.append(metrics)

        except Exception as exc:
            logger.warning(f"Contraction scan error for {symbol}: {exc}")

    logger.info(f"Contraction scan complete: {len(results)} stocks matched")
    return results


async def run_ppc_scan(scan_date: str, data: dict[str, pd.DataFrame] | None = None) -> list[dict]:
    """Run PPC scan. Fetches data if not provided."""
    if data is None:
        data = await fetch_all_stocks(scan_date)
    return _scan_ppc(data, scan_date)


async def run_npc_scan(scan_date: str, data: dict[str, pd.DataFrame] | None = None) -> list[dict]:
    """Run NPC scan. Fetches data if not provided."""
    if data is None:
        data = await fetch_all_stocks(scan_date)
    return _scan_npc(data, scan_date)


async def run_contraction_scan(scan_date: str, data: dict[str, pd.DataFrame] | None = None) -> list[dict]:
    """Run Contraction scan. Fetches data if not provided."""
    if data is None:
        data = await fetch_all_stocks(scan_date)
    return _scan_contraction(data, scan_date)


async def run_all_scans(scan_date: str) -> list[dict]:
    """
    Run all three scans using a single shared data download.
    This is much faster than running each scan independently.
    """
    data = await fetch_all_stocks(scan_date)
    logger.info(f"Data fetched for {len(data)} symbols. Running all scans...")

    ppc_results = _scan_ppc(data, scan_date)
    npc_results = _scan_npc(data, scan_date)
    contraction_results = _scan_contraction(data, scan_date)

    all_results = ppc_results + npc_results + contraction_results
    logger.info(
        f"All scans complete: {len(ppc_results)} PPC, "
        f"{len(npc_results)} NPC, {len(contraction_results)} Contraction"
    )
    return all_results
