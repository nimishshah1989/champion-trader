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
    Fires the job in the background and returns immediately — the scan can
    take 30–60 s (yfinance data fetch), which would otherwise time out.
    Poll GET /rs-strategy/status to see updated results.
    """
    logger.info("[RS-EMA] Manual run triggered via API")
    asyncio.create_task(run_rs_ema_daily())
    return {"message": "RS EMA scan started — poll /rs-strategy/status for results."}
