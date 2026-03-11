"""
regime_classifier.py — Classifies current market into one of four regimes.

Inputs (computed from yfinance data):
  - Nifty 50 ADX (14-day)
  - India VIX (^INDIAVIX)
  - Price vs 150-day SMA of Nifty 50
  - Hurst exponent on Nifty 50 closes (90-day window)

Output: one of:
  "TRENDING_BULL"    — ADX>25, VIX<15, price above rising SMA
  "RANGING_QUIET"    — ADX<20, low VIX, flat SMA, Hurst < 0.5
  "HIGH_VOLATILITY"  — VIX>20 or ADX trending but erratic
  "WEAKENING_BEAR"   — Price below declining SMA, NPC dominant
"""

import logging
from datetime import datetime, date as date_type

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats as scipy_stats

from backend.database import SessionLocal, RegimeLog

logger = logging.getLogger(__name__)


def calculate_adx(df: pd.DataFrame, period: int = 14) -> float:
    """Calculate Average Directional Index from OHLCV DataFrame."""
    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values

    # True Range
    tr = np.maximum(high[1:] - low[1:],
                    np.abs(high[1:] - close[:-1]),
                    np.abs(low[1:] - close[:-1]))

    # Directional Movement
    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # Smoothed averages (Wilder's smoothing)
    atr = np.zeros(len(tr))
    plus_di_arr = np.zeros(len(tr))
    minus_di_arr = np.zeros(len(tr))

    atr[period - 1] = np.mean(tr[:period])
    smoothed_plus = np.mean(plus_dm[:period])
    smoothed_minus = np.mean(minus_dm[:period])

    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        smoothed_plus = (smoothed_plus * (period - 1) + plus_dm[i]) / period
        smoothed_minus = (smoothed_minus * (period - 1) + minus_dm[i]) / period

        if atr[i] > 0:
            plus_di_arr[i] = 100 * smoothed_plus / atr[i]
            minus_di_arr[i] = 100 * smoothed_minus / atr[i]

    # DX and ADX
    dx = np.zeros(len(tr))
    for i in range(period, len(tr)):
        di_sum = plus_di_arr[i] + minus_di_arr[i]
        if di_sum > 0:
            dx[i] = 100 * abs(plus_di_arr[i] - minus_di_arr[i]) / di_sum

    # ADX = smoothed DX
    adx_values = np.zeros(len(tr))
    adx_start = 2 * period - 1
    if adx_start < len(dx):
        adx_values[adx_start] = np.mean(dx[period:adx_start + 1])
        for i in range(adx_start + 1, len(dx)):
            adx_values[i] = (adx_values[i - 1] * (period - 1) + dx[i]) / period

    return float(adx_values[-1]) if len(adx_values) > 0 else 0.0


def calculate_hurst_exponent(series: np.ndarray, max_lag: int = 20) -> float:
    """
    Calculate Hurst exponent using R/S analysis.
    H < 0.5: mean-reverting, H = 0.5: random walk, H > 0.5: trending
    """
    if len(series) < max_lag * 2:
        return 0.5  # Default to random walk if insufficient data

    lags = range(2, max_lag + 1)
    rs_values = []

    for lag in lags:
        # Split into sub-series
        n_subseries = len(series) // lag
        if n_subseries < 1:
            continue

        rs_list = []
        for i in range(n_subseries):
            subseries = series[i * lag:(i + 1) * lag]
            mean_val = np.mean(subseries)
            deviations = subseries - mean_val
            cumulative = np.cumsum(deviations)
            r = np.max(cumulative) - np.min(cumulative)
            s = np.std(subseries, ddof=1)
            if s > 0:
                rs_list.append(r / s)

        if rs_list:
            rs_values.append((np.log(lag), np.log(np.mean(rs_list))))

    if len(rs_values) < 3:
        return 0.5

    log_lags, log_rs = zip(*rs_values)
    slope, _, _, _, _ = scipy_stats.linregress(log_lags, log_rs)

    # Clamp to reasonable range
    return float(np.clip(slope, 0.0, 1.0))


async def classify_regime() -> dict:
    """
    Classify current market regime.
    Returns dict with regime, all inputs, and metadata.
    """
    logger.info("Running regime classification...")

    # Fetch Nifty 50 data (6 months for 150-day SMA)
    nifty = yf.download("^NSEI", period="8mo", progress=False)
    if nifty.empty or len(nifty) < 150:
        logger.error("Insufficient Nifty data for regime classification")
        return {"regime": "RANGING_QUIET", "error": "insufficient_data"}

    # Flatten MultiIndex columns if present
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)

    # ADX
    adx = calculate_adx(nifty, period=14)

    # VIX
    try:
        vix_data = yf.download("^INDIAVIX", period="5d", progress=False)
        if isinstance(vix_data.columns, pd.MultiIndex):
            vix_data.columns = vix_data.columns.get_level_values(0)
        india_vix = float(vix_data["Close"].iloc[-1]) if not vix_data.empty else 15.0
    except Exception:
        india_vix = 15.0  # Default if VIX unavailable

    # Price vs 150-day SMA
    nifty_close = float(nifty["Close"].iloc[-1])
    sma_150 = float(nifty["Close"].rolling(window=150).mean().iloc[-1])
    price_vs_sma_pct = ((nifty_close - sma_150) / sma_150) * 100

    # SMA slope (20-day change)
    sma_series = nifty["Close"].rolling(window=150).mean()
    sma_now = float(sma_series.iloc[-1])
    sma_20ago = float(sma_series.iloc[-20]) if len(sma_series) >= 20 else sma_now
    sma_slope_pct = ((sma_now - sma_20ago) / sma_20ago) * 100 if sma_20ago > 0 else 0

    # Hurst exponent (90-day window)
    closes_90d = nifty["Close"].iloc[-90:].values.astype(float)
    hurst = calculate_hurst_exponent(closes_90d)

    # Classification logic
    if (adx > 25 and india_vix < 15 and price_vs_sma_pct > 3 and sma_slope_pct > 0.5):
        regime = "TRENDING_BULL"
    elif (price_vs_sma_pct < -5 and sma_slope_pct < -0.5):
        regime = "WEAKENING_BEAR"
    elif india_vix > 20:
        regime = "HIGH_VOLATILITY"
    elif (adx < 20 and hurst < 0.5 and abs(price_vs_sma_pct) < 5):
        regime = "RANGING_QUIET"
    elif adx > 25 and price_vs_sma_pct > 0:
        regime = "TRENDING_BULL"
    elif india_vix > 16 and adx > 20:
        regime = "HIGH_VOLATILITY"
    else:
        regime = "RANGING_QUIET"

    result = {
        "regime": regime,
        "nifty_adx": round(adx, 2),
        "india_vix": round(india_vix, 2),
        "nifty_close": round(nifty_close, 2),
        "nifty_sma150": round(sma_150, 2),
        "price_vs_sma_pct": round(price_vs_sma_pct, 2),
        "sma_slope_pct": round(sma_slope_pct, 4),
        "hurst_exponent": round(hurst, 4),
        "classified_at": datetime.now().isoformat(),
    }

    # Log to database
    _log_regime(result)

    logger.info(f"Regime classified: {regime} (ADX={adx:.1f}, VIX={india_vix:.1f}, Hurst={hurst:.3f})")
    return result


def _log_regime(result: dict):
    """Persist regime classification to database."""
    db = SessionLocal()
    try:
        existing = db.query(RegimeLog).filter(
            RegimeLog.regime_date == date_type.today()
        ).first()

        if existing:
            existing.regime = result["regime"]
            existing.nifty_adx = result["nifty_adx"]
            existing.india_vix = result["india_vix"]
            existing.hurst_exponent = result["hurst_exponent"]
            existing.nifty_close = result["nifty_close"]
            existing.nifty_sma150 = result["nifty_sma150"]
        else:
            log_entry = RegimeLog(
                regime_date=date_type.today(),
                regime=result["regime"],
                nifty_adx=result["nifty_adx"],
                india_vix=result["india_vix"],
                hurst_exponent=result["hurst_exponent"],
                nifty_close=result["nifty_close"],
                nifty_sma150=result["nifty_sma150"],
            )
            db.add(log_entry)

        db.commit()
    except Exception as e:
        logger.error(f"Failed to log regime: {e}")
        db.rollback()
    finally:
        db.close()


def get_latest_regime() -> dict:
    """Get the most recent regime classification from DB."""
    db = SessionLocal()
    try:
        entry = db.query(RegimeLog).order_by(RegimeLog.regime_date.desc()).first()
        if entry:
            return {
                "regime": entry.regime,
                "date": str(entry.regime_date),
                "nifty_adx": entry.nifty_adx,
                "india_vix": entry.india_vix,
                "hurst_exponent": entry.hurst_exponent,
                "param_bank_version": entry.param_bank_version,
            }
        return {"regime": "UNKNOWN", "date": None}
    finally:
        db.close()
