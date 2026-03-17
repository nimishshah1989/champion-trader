"""baseline_scanner.py -- Runs scans with FROZEN default parameters for A/B comparison.

Every day after the main scan (which uses optimized PARAMETERS), this module
runs the same 3 scans using DEFAULT_PARAMETERS. Results are stored in
baseline_scan_results. A daily comparison row is computed showing:
  - Stocks found by BOTH parameter sets (overlap)
  - Stocks found ONLY by optimized params (optimizer advantage)
  - Stocks found ONLY by defaults (optimizer missed)

Over time, this tells us whether AutoOptimize is finding better setups.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

from backend.database import (
    BaselineScanResult,
    DailyScanComparison,
    ScanResult,
    SessionLocal,
)
from backend.intelligence.strategy import DEFAULT_PARAMETERS, PARAMETERS
from backend.services.technical import (
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

MIN_ADT_DEFAULT = int(DEFAULT_PARAMETERS["min_adt_crore"] * 1_00_00_000)


def _build_metrics(symbol: str, df: pd.DataFrame, scan_date: str) -> dict:
    """Compute metrics for a single stock (same logic as scanner_engine)."""
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

    scan_date_obj = date.fromisoformat(scan_date) if isinstance(scan_date, str) else scan_date

    return {
        "scan_date": scan_date_obj,
        "symbol": symbol,
        "close_price": Decimal(str(round(float(df["Close"].iloc[-1]), 2))),
        "trp": Decimal(str(round(float(trp.iloc[-1]), 2))) if pd.notna(trp.iloc[-1]) else None,
        "trp_ratio": round(float(trp_ratio.iloc[-1]), 2) if pd.notna(trp_ratio.iloc[-1]) else None,
        "volume_ratio": round(float(vol_ratio.iloc[-1]), 2) if pd.notna(vol_ratio.iloc[-1]) else None,
        "close_position": round(float(close_pos.iloc[-1]), 2) if pd.notna(close_pos.iloc[-1]) else None,
        "stage": stage,
        "base_days": base_days,
        "base_quality": base_quality,
        "passes_liquidity_filter": adt >= MIN_ADT_DEFAULT,
        "trigger_level": Decimal(str(round(float(df["High"].iloc[-1]), 2))),
    }


def _bucket(stage: str, base_days: int, base_quality: str) -> str:
    """Watchlist bucket using DEFAULT min_base_days."""
    min_days = int(DEFAULT_PARAMETERS["min_base_days"])
    if stage in ("S1B", "S2") and base_days >= min_days and base_quality in ("SMOOTH", "MIXED"):
        return "READY"
    if stage in ("S1B", "S2") and base_days >= 15:
        return "NEAR"
    return "AWAY"


def run_baseline_scans(
    all_data: dict[str, pd.DataFrame], scan_date: str
) -> list[dict]:
    """Run PPC/NPC/Contraction using DEFAULT_PARAMETERS. Returns list of result dicts."""
    params = DEFAULT_PARAMETERS
    results: list[dict] = []

    for symbol, df in all_data.items():
        try:
            if len(df) < 30:
                continue
            m = _build_metrics(symbol, df, scan_date)
            if not m["passes_liquidity_filter"]:
                continue

            is_green = df["Close"].iloc[-1] > df["Open"].iloc[-1]
            is_red = df["Close"].iloc[-1] < df["Open"].iloc[-1]
            tr = m["trp_ratio"]
            cp = m["close_position"]
            vr = m["volume_ratio"]

            # PPC check
            if (tr and cp and vr and is_green
                    and tr >= params["ppc_trp_ratio_min"]
                    and cp >= params["ppc_close_position_min"]
                    and vr >= params["ppc_volume_ratio_min"]):
                m["scan_type"] = "PPC"
                m["watchlist_bucket"] = _bucket(m["stage"], m["base_days"], m["base_quality"])
                m["param_snapshot"] = json.dumps(params)
                results.append(dict(m))
                continue

            # NPC check
            if (tr and cp and vr and is_red
                    and tr >= params["npc_trp_ratio_min"]
                    and cp <= params["npc_close_position_max"]
                    and vr >= params["npc_volume_ratio_min"]):
                m["scan_type"] = "NPC"
                m["watchlist_bucket"] = _bucket(m["stage"], m["base_days"], m["base_quality"])
                m["param_snapshot"] = json.dumps(params)
                results.append(dict(m))
                continue

            # Contraction check
            from backend.services.technical import calculate_atr_slope
            atr_slope = calculate_atr_slope(df, atr_period=14, slope_bars=5)
            narrowing = count_narrowing_candles(df, lookback=10, tolerance=0.05)
            near_res = price_near_resistance(
                df, lookback=60, threshold_pct=params["contraction_resistance_pct"]
            )
            if atr_slope < 0 and narrowing >= params["contraction_narrowing_min"] and near_res:
                m["scan_type"] = "CONTRACTION"
                m["watchlist_bucket"] = _bucket(m["stage"], m["base_days"], m["base_quality"])
                m["param_snapshot"] = json.dumps(params)
                results.append(dict(m))

        except Exception as exc:
            logger.warning(f"Baseline scan error for {symbol}: {exc}")

    logger.info(f"[BASELINE] Scan complete: {len(results)} stocks matched with default params")
    return results


def save_and_compare(baseline_results: list[dict]) -> dict:
    """Save baseline results to DB, compute comparison with today's optimized scan."""
    today = date.today()
    db = SessionLocal()
    try:
        # Clear today's baseline results (idempotent)
        db.query(BaselineScanResult).filter(
            BaselineScanResult.scan_date == today
        ).delete()

        for r in baseline_results:
            db.add(BaselineScanResult(**r))

        # Get today's optimized scan results
        optimized = db.query(ScanResult).filter(ScanResult.scan_date == today).all()
        opt_symbols = {s.symbol for s in optimized}
        base_symbols = {r["symbol"] for r in baseline_results}

        overlap = opt_symbols & base_symbols
        opt_only = opt_symbols - base_symbols
        base_only = base_symbols - opt_symbols

        # Upsert comparison row
        existing = db.query(DailyScanComparison).filter(
            DailyScanComparison.compare_date == today
        ).first()

        comparison_data = {
            "compare_date": today,
            "optimized_count": len(opt_symbols),
            "baseline_count": len(base_symbols),
            "overlap_count": len(overlap),
            "optimized_only": json.dumps(sorted(opt_only)),
            "baseline_only": json.dumps(sorted(base_only)),
            "overlap_symbols": json.dumps(sorted(overlap)),
            "optimized_params": json.dumps(dict(PARAMETERS)),
            "baseline_params": json.dumps(DEFAULT_PARAMETERS),
        }

        if existing:
            for k, v in comparison_data.items():
                if k != "compare_date":
                    setattr(existing, k, v)
        else:
            db.add(DailyScanComparison(**comparison_data))

        db.commit()

        result = {
            "date": str(today),
            "optimized_found": len(opt_symbols),
            "baseline_found": len(base_symbols),
            "overlap": len(overlap),
            "optimized_only": sorted(opt_only),
            "baseline_only": sorted(base_only),
        }
        logger.info(
            f"[BASELINE] Comparison: {len(opt_symbols)} optimized, "
            f"{len(base_symbols)} baseline, {len(overlap)} overlap, "
            f"{len(opt_only)} opt-only, {len(base_only)} base-only"
        )
        return result

    except Exception as exc:
        logger.error(f"[BASELINE] Save/compare failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()


def get_comparison_history(days: int = 30) -> list[dict]:
    """Return last N days of scan comparisons."""
    db = SessionLocal()
    try:
        rows = (
            db.query(DailyScanComparison)
            .order_by(DailyScanComparison.compare_date.desc())
            .limit(days)
            .all()
        )
        return [
            {
                "date": str(r.compare_date),
                "optimized_count": r.optimized_count,
                "baseline_count": r.baseline_count,
                "overlap": r.overlap_count,
                "optimized_only": json.loads(r.optimized_only or "[]"),
                "baseline_only": json.loads(r.baseline_only or "[]"),
            }
            for r in rows
        ]
    finally:
        db.close()
