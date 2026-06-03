"""
RS EMA50×200 paper-trading strategy — API endpoints.

GET  /rs-strategy/status    — portfolio overview, open positions, equity curve
GET  /rs-strategy/trades    — full trade ledger (open + closed)
POST /rs-strategy/run-now   — manually trigger today's signal scan + position update
"""

import asyncio
import logging

from fastapi import APIRouter

from backend.intelligence.rs_ema_strategy import (
    get_all_trades,
    get_portfolio_status,
    run_rs_ema_daily,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rs-strategy", tags=["RS Strategy"])


@router.get("/status")
def rs_status():
    """Current RS EMA50×200 paper portfolio — equity, open positions, closed summary."""
    return get_portfolio_status()


@router.get("/trades")
def rs_trades():
    """Full trade ledger for the active RS EMA run."""
    return get_all_trades()


@router.post("/run-now")
async def rs_run_now():
    """
    Manually trigger the RS EMA50×200 daily scan.
    Same logic as the 16:30 IST scheduled job — fetches latest prices,
    processes exits on open positions, opens new golden-cross positions.
    """
    logger.info("[RS-EMA] Manual run triggered via API")
    result = await run_rs_ema_daily()
    return {
        "message": "RS EMA daily run complete",
        "result": result,
    }
