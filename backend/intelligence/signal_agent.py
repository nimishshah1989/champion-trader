"""
signal_agent.py — Ranked setup card generator.

After daily scan, ranks all detected setups by composite quality score.
Each setup card contains: entry zone, stop, targets, R:R, position size,
historical context from RAG.

Called by CIO Agent to get top N setups for the Daily Brief.
"""

import logging
from datetime import datetime
from typing import Optional

from backend.config import settings
from backend.database import SessionLocal, ScanResult, Trade
from backend.intelligence.strategy import PARAMETERS
from backend.services.position_calculator import calculate_position
from backend.services.trading_rules import TRADING_RULES

logger = logging.getLogger(__name__)


def compute_setup_score(scan_result: dict) -> float:
    """
    Compute composite quality score (0-100) for a scan result.

    Factors:
      - Signal strength (TRP ratio, volume ratio)
      - Base quality (base days, base quality grade)
      - Stage alignment (S2 > S1B)
      - Liquidity (ADT)
    """
    score = 0.0

    # Signal strength (0-40 points)
    trp_ratio = scan_result.get("trp_ratio") or 0
    vol_ratio = scan_result.get("volume_ratio") or 0
    close_pos = scan_result.get("close_position") or 0

    # TRP ratio: higher is better, max contribution at 3.0+
    trp_score = min(trp_ratio / 3.0, 1.0) * 15

    # Volume ratio: higher is better, max at 3.0+
    vol_score = min(vol_ratio / 3.0, 1.0) * 15

    # Close position: for PPC, higher is better; for NPC, lower is better
    scan_type = scan_result.get("scan_type", "PPC")
    if scan_type == "PPC":
        close_score = min(close_pos / 0.90, 1.0) * 10
    elif scan_type == "NPC":
        close_score = min((1 - close_pos) / 0.80, 1.0) * 10
    else:
        close_score = 5  # Neutral for contraction

    score += trp_score + vol_score + close_score

    # Base quality (0-25 points)
    base_days = scan_result.get("base_days") or 0
    base_quality = scan_result.get("base_quality", "")

    base_days_score = min(base_days / 40, 1.0) * 15
    quality_map = {"SMOOTH": 10, "MIXED": 6, "CHOPPY": 2}
    base_qual_score = quality_map.get(base_quality, 0)

    score += base_days_score + base_qual_score

    # Stage alignment (0-20 points)
    stage = scan_result.get("stage", "")
    stage_scores = {"S2": 20, "S1B": 12, "S1": 5}
    score += stage_scores.get(stage, 0)

    # Liquidity (0-15 points)
    adt = scan_result.get("adt") or 0
    adt_crore = adt / 1e7
    adt_score = min(adt_crore / 10.0, 1.0) * 15
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


async def get_top_setups(
    top_n: int = 5,
    account_value: float = 500000,
    rpt_pct: float = 0.5,
    scan_date: Optional[str] = None,
) -> list[dict]:
    """
    Get top N ranked setup cards from the latest scan results.

    Queries the scan_results table for the most recent scan date,
    scores each result, generates setup cards, and returns top N.
    """
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

        # Convert to dicts and score
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

            card = generate_setup_card(scan_dict, account_value, rpt_pct)
            setup_cards.append(card)

        # Sort by composite score descending
        setup_cards.sort(key=lambda x: x["composite_score"], reverse=True)

        return setup_cards[:top_n]

    finally:
        db.close()
