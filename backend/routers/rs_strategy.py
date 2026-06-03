"""
RS EMA50×200 paper-trading strategy — API endpoints.

GET  /rs-strategy/status    — both Portfolio A and B overview
GET  /rs-strategy/trades    — trade ledgers for A and B
POST /rs-strategy/run-now   — manually trigger today's scan (fires in background)
"""

import asyncio
import logging

from fastapi import APIRouter

from backend.intelligence.rs_ema_strategy import (
    get_both_portfolios_status,
    get_both_portfolios_trades,
    run_rs_ema_daily,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rs-strategy", tags=["RS Strategy"])


@router.get("/status")
def rs_status():
    """Current RS EMA50×200 paper portfolio status for both A and B."""
    return get_both_portfolios_status()


@router.get("/trades")
def rs_trades():
    """Full trade ledger for Portfolio A and B."""
    return get_both_portfolios_trades()


@router.post("/run-now")
async def rs_run_now():
    """
    Manually trigger the RS EMA50×200 daily scan for both portfolios.
    Fires in background — returns immediately. Poll /status for results.
    """
    logger.info("[RS-EMA] Manual run triggered via API")
    asyncio.create_task(run_rs_ema_daily())
    return {"message": "RS EMA scan started for Portfolio A and B — poll /rs-strategy/status for results."}
