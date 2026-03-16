"""
signal_agent.py — Ranked setup card generator.

After daily scan, ranks all detected setups by composite quality score.
Each setup card contains: entry zone, stop, targets, R:R, position size,
historical context from RAG.

Called by CIO Agent to get top N setups for the Daily Brief.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from backend.config import settings
from backend.database import SessionLocal, ScanResult, Trade
from backend.services.position_calculator import calculate_position
from backend.services.trading_rules import TRADING_RULES

logger = logging.getLogger(__name__)


def _get_effective_parameters() -> dict:
    """
    Get the effective parameters: base PARAMETERS merged with regime overrides.
    This is the single source of truth for all signal thresholds.
    """
    from backend.intelligence.parameter_banks import get_active_parameters
    from backend.intelligence.regime_classifier import get_latest_regime

    regime_info = get_latest_regime()
    regime = regime_info.get("regime", "RANGING_QUIET")
    return get_active_parameters(regime)


def compute_setup_score(scan_result: dict, params: dict | None = None) -> float:
    """
    Compute composite quality score (0-100) for a scan result.

    Uses live PARAMETERS (merged with regime overrides) for all thresholds.
    Factors:
      - Signal strength (TRP ratio, volume ratio)
      - Base quality (base days, base quality grade)
      - Stage alignment (S2 > S1B)
      - Liquidity (ADT)
    """
    if params is None:
        params = _get_effective_parameters()

    score = 0.0

    # Signal strength (0-40 points)
    trp_ratio = scan_result.get("trp_ratio") or 0
    vol_ratio = scan_result.get("volume_ratio") or 0
    close_pos = scan_result.get("close_position") or 0

    # Use PARAMETERS for normalization — higher threshold = stricter scoring
    ppc_trp_min = params.get("ppc_trp_ratio_min", 1.5)
    ppc_vol_min = params.get("ppc_volume_ratio_min", 1.5)
    ppc_close_min = params.get("ppc_close_position_min", 0.60)
    npc_close_max = params.get("npc_close_position_max", 0.40)

    # TRP ratio: normalize against 2x the threshold (max contribution at 2x min)
    trp_ceiling = ppc_trp_min * 2
    trp_score = min(trp_ratio / trp_ceiling, 1.0) * 15

    # Volume ratio: normalize against 2x the threshold
    vol_ceiling = ppc_vol_min * 2
    vol_score = min(vol_ratio / vol_ceiling, 1.0) * 15

    # Close position: for PPC, higher is better; for NPC, lower is better
    scan_type = scan_result.get("scan_type", "PPC")
    if scan_type == "PPC":
        close_score = min(close_pos / max(ppc_close_min + 0.10, 0.70), 1.0) * 10
    elif scan_type == "NPC":
        close_score = min((1 - close_pos) / max(1 - npc_close_max + 0.10, 0.70), 1.0) * 10
    else:
        close_score = 5  # Neutral for contraction

    score += trp_score + vol_score + close_score

    # Base quality (0-25 points)
    base_days = scan_result.get("base_days") or 0
    base_quality = scan_result.get("base_quality", "")
    min_base = params.get("min_base_days", 20)

    # Normalize base days against 2x minimum
    base_days_score = min(base_days / (min_base * 2), 1.0) * 15
    quality_map = {"SMOOTH": 10, "MIXED": 6, "CHOPPY": 2}
    base_qual_score = quality_map.get(base_quality, 0)

    score += base_days_score + base_qual_score

    # Stage alignment (0-20 points)
    stage = scan_result.get("stage", "")
    stage_scores = {"S2": 20, "S1B": 12, "S1": 5}
    score += stage_scores.get(stage, 0)

    # Liquidity (0-15 points)
    adt = float(scan_result.get("adt") or 0)
    adt_crore = adt / 1e7
    min_adt = params.get("min_adt_crore", 1.0)
    adt_ceiling = max(min_adt * 10, 10.0)
    adt_score = min(adt_crore / adt_ceiling, 1.0) * 15
    score += adt_score

    return round(min(score, 100), 1)


def generate_setup_card(scan_result: dict, account_value: float, rpt_pct: float = 0.5) -> dict:
    """
    Generate a complete setup card from a scan result.

    Includes entry zone, stop loss, all targets, position sizing, R:R ratio.
    """
    symbol = scan_result.get("symbol", "")
    close_price = scan_result.get("close_price", 0)
    trp = scan_result.get("trp") or scan_result.get("avg_trp") or 2.0
    avg_trp = scan_result.get("avg_trp") or trp
    scan_type = scan_result.get("scan_type", "PPC")

    # Use avg_trp for position sizing (more stable than single-day TRP)
    trp_pct = avg_trp

    # Entry zone
    if scan_type == "CONTRACTION":
        trigger = scan_result.get("trigger_level", close_price * 1.01)
        entry_price = trigger  # Breakout entry
    else:
        entry_price = close_price  # PPC/NPC entry near close

    # Stop loss
    trp_value = entry_price * (trp_pct / 100)
    stop_price = round(entry_price - trp_value, 2)

    # Targets using methodology exit ladder
    target_2r = round(entry_price + (2 * trp_value), 2)
    target_ne = round(entry_price + (TRADING_RULES["normal_extension_x"] * trp_value), 2)
    target_ge = round(entry_price + (TRADING_RULES["great_extension_x"] * trp_value), 2)
    target_ee = round(entry_price + (TRADING_RULES["extreme_extension_x"] * trp_value), 2)

    # Position sizing
    risk_per_trade = account_value * (rpt_pct / 100)
    risk_per_share = entry_price - stop_price

    if risk_per_share > 0:
        position_size = int(risk_per_trade / risk_per_share)
        half_qty = position_size // 2
    else:
        position_size = 0
        half_qty = 0

    position_value = position_size * entry_price

    # R:R ratio (to 2R target)
    reward = target_2r - entry_price
    risk = entry_price - stop_price
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0

    # Composite score
    composite_score = compute_setup_score(scan_result)

    return {
        "symbol": symbol,
        "scan_type": scan_type,
        "composite_score": composite_score,
        "entry_price": round(entry_price, 2),
        "stop_price": stop_price,
        "trp_pct": round(trp_pct, 2),
        "trp_value": round(trp_value, 2),
        "target_2r": target_2r,
        "target_ne": target_ne,
        "target_ge": target_ge,
        "target_ee": target_ee,
        "rr_ratio": rr_ratio,
        "position_size": position_size,
        "half_qty": half_qty,
        "position_value": round(position_value, 2),
        "risk_amount": round(risk_per_trade, 2),
        "stage": scan_result.get("stage", ""),
        "base_days": scan_result.get("base_days", 0),
        "base_quality": scan_result.get("base_quality", ""),
        "volume_ratio": scan_result.get("volume_ratio"),
        "trp_ratio": scan_result.get("trp_ratio"),
    }


def _passes_minimum_thresholds(scan_dict: dict, params: dict) -> bool:
    """
    Check if a scan result meets the minimum thresholds from PARAMETERS.
    This is where the learning loop closes: optimized thresholds filter signals.
    """
    scan_type = scan_dict.get("scan_type", "PPC")
    trp_ratio = scan_dict.get("trp_ratio") or 0
    vol_ratio = scan_dict.get("volume_ratio") or 0
    close_pos = scan_dict.get("close_position") or 0
    base_days = scan_dict.get("base_days") or 0
    adt = float(scan_dict.get("adt") or 0)
    adt_crore = adt / 1e7

    # Liquidity and base days — universal
    if adt_crore < params.get("min_adt_crore", 1.0):
        return False
    if base_days < params.get("min_base_days", 20):
        return False

    if scan_type == "PPC":
        if trp_ratio < params.get("ppc_trp_ratio_min", 1.5):
            return False
        if close_pos < params.get("ppc_close_position_min", 0.60):
            return False
        if vol_ratio < params.get("ppc_volume_ratio_min", 1.5):
            return False
    elif scan_type == "NPC":
        if trp_ratio < params.get("npc_trp_ratio_min", 1.5):
            return False
        if close_pos > params.get("npc_close_position_max", 0.40):
            return False
        if vol_ratio < params.get("npc_volume_ratio_min", 1.5):
            return False

    return True


async def get_top_setups(
    top_n: int = 5,
    account_value: float = 500000,
    rpt_pct: float = 0.5,
    scan_date: Optional[str] = None,
) -> list[dict]:
    """
    Get top N ranked setup cards from the latest scan results.

    Uses regime-aware PARAMETERS for both filtering and scoring.
    This is the closed loop: AutoOptimize → strategy.py → here.
    """
    params = _get_effective_parameters()
    db = SessionLocal()
    try:
        # Get latest scan date
        if scan_date is None:
            latest = db.query(ScanResult.scan_date).order_by(
                ScanResult.scan_date.desc()
            ).first()
            if not latest:
                return []
            scan_date = str(latest[0])

        # Get all scan results for the date
        results = db.query(ScanResult).filter(
            ScanResult.scan_date == scan_date
        ).all()

        if not results:
            return []

        # Convert to dicts, filter by learned thresholds, then score
        setup_cards = []
        for r in results:
            scan_dict = {
                "symbol": r.symbol,
                "scan_type": r.scan_type,
                "close_price": r.close_price,
                "trp_ratio": r.trp_ratio,
                "close_position": r.close_position,
                "volume_ratio": r.volume_ratio,
                "trp": getattr(r, "trp", None),
                "avg_trp": getattr(r, "avg_trp", None),
                "stage": r.stage,
                "base_days": r.base_days,
                "base_quality": r.base_quality,
                "trigger_level": r.trigger_level,
                "adt": getattr(r, "avg_daily_turnover", 0) or 0,
            }

            # Filter against learned/regime-adjusted thresholds
            if not _passes_minimum_thresholds(scan_dict, params):
                continue

            card = generate_setup_card(scan_dict, account_value, rpt_pct)
            setup_cards.append(card)

        # Sort by composite score descending
        setup_cards.sort(key=lambda x: x["composite_score"], reverse=True)

        logger.info(
            f"Top setups: {len(setup_cards)} passed filters "
            f"(from {len(results)} scans, params version: regime-adjusted)"
        )

        return setup_cards[:top_n]

    finally:
        db.close()
