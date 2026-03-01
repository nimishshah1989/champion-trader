"""
Batch data fetcher using yfinance.
Downloads OHLCV history for NSE stocks in batches to avoid API limits.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
HISTORY_MONTHS = 7  # Covers 150-day SMA requirement


def _download_batch(symbols: list[str], period_start: str, period_end: str) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV data for a batch of symbols.
    Returns dict mapping clean symbol (no .NS) → DataFrame.
    """
    if not symbols:
        return {}

    result: dict[str, pd.DataFrame] = {}

    try:
        # yf.download returns MultiIndex columns for multiple symbols
        data = yf.download(
            tickers=symbols,
            start=period_start,
            end=period_end,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )

        if data.empty:
            logger.warning("Empty response from yfinance for batch")
            return {}

        if len(symbols) == 1:
            # Single symbol: columns are flat (Open, High, Low, Close, Volume)
            symbol = symbols[0]
            clean = strip_ns_suffix(symbol)
            if not data.empty and len(data) > 0:
                df = data.copy()
                df = df.dropna(subset=["Close"])
                if len(df) >= 30:
                    result[clean] = df
                else:
                    logger.warning(f"{clean}: Only {len(df)} rows after cleanup, skipping")
        else:
            # Multiple symbols: MultiIndex columns (symbol, field)
            for symbol in symbols:
                clean = strip_ns_suffix(symbol)
                try:
                    if symbol in data.columns.get_level_values(0):
                        df = data[symbol].copy()
                        df = df.dropna(subset=["Close"])
                        if len(df) >= 30:
                            result[clean] = df
                        else:
                            logger.warning(f"{clean}: Only {len(df)} rows after cleanup, skipping")
                except (KeyError, TypeError) as exc:
                    logger.warning(f"{clean}: Failed to extract data — {exc}")

    except Exception as exc:
        logger.error(f"yfinance batch download failed: {exc}")

    return result


def fetch_all_stocks_sync(scan_date: str | None = None) -> dict[str, pd.DataFrame]:
    """
    Download 7 months of OHLCV for all NIFTY 200 stocks.
    Processes in batches of 50 to avoid rate limits.

    Returns dict mapping symbol → DataFrame with columns:
    Open, High, Low, Close, Volume
    """
    all_symbols = get_yfinance_symbols()

    if scan_date:
        end_date = scan_date
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")

    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=HISTORY_MONTHS * 30)).strftime("%Y-%m-%d")

    logger.info(f"Fetching {len(all_symbols)} stocks from {start_date} to {end_date}")

    all_data: dict[str, pd.DataFrame] = {}
    total_batches = (len(all_symbols) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(all_symbols))
        batch = all_symbols[start:end]

        logger.info(f"Batch {batch_idx + 1}/{total_batches}: downloading {len(batch)} symbols")

        batch_result = _download_batch(batch, start_date, end_date)
        all_data.update(batch_result)

        logger.info(f"Batch {batch_idx + 1} complete: got {len(batch_result)} symbols")

    logger.info(f"Total: {len(all_data)} symbols with valid data out of {len(all_symbols)}")
    return all_data


async def fetch_all_stocks(scan_date: str | None = None) -> dict[str, pd.DataFrame]:
    """
    Async wrapper — runs yfinance download in a thread so it
    doesn't block the FastAPI event loop.
    """
    return await asyncio.to_thread(fetch_all_stocks_sync, scan_date)
