import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.middleware.decimal_fix import DecimalFixMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

from backend.routers import (
    journal,
    scanner,
    trades,
    watchlist,
)
from backend.routers.intelligence import router as intelligence_router
from backend.routers.intelligence_strategy import router as intelligence_strategy_router
from backend.routers.rs_strategy import router as rs_strategy_router
from backend.routers.kite_auth import router as kite_auth_router


# ── APScheduler Setup ────────────────────────────────────────────────

scheduler = None


def _setup_scheduler():
    """Configure APScheduler with all v2 pipeline jobs."""
    global scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        import pytz

        IST = pytz.timezone("Asia/Kolkata")
        scheduler = AsyncIOScheduler(timezone=IST)

        # Risk Guardian — every 10 minutes during market hours (9:15–15:30 IST)
        from backend.intelligence.risk_guardian import monitor_positions

        scheduler.add_job(
            monitor_positions,
            CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/10", timezone=IST),
            id="risk_guardian",
            name="Risk Guardian: Position Monitor",
        )

        # Learning Agent — check for closed trades every 30 minutes
        from backend.intelligence.learning_agent import process_closed_trades

        scheduler.add_job(
            process_closed_trades,
            CronTrigger(day_of_week="mon-fri", hour="9-16", minute="0,30", timezone=IST),
            id="learning_agent",
            name="Learning Agent: Post-Mortem Generator",
        )

        # Regime Classifier — daily at 16:45 IST
        from backend.intelligence.regime_classifier import classify_regime

        scheduler.add_job(
            classify_regime,
            CronTrigger(day_of_week="mon-fri", hour=16, minute=45, timezone=IST),
            id="regime_classifier",
            name="Regime Classifier: Daily Classification",
        )

        # CIO Agent — daily at 17:00 IST
        from backend.intelligence.cio_agent import generate_brief

        scheduler.add_job(
            generate_brief,
            CronTrigger(day_of_week="mon-fri", hour=17, minute=0, timezone=IST),
            id="cio_agent",
            name="CIO Agent: Daily Brief",
        )

        # Kite morning login alert — 08:45 IST, user taps link to authorize
        from backend.intelligence.kite_morning_alert import send_kite_login_alert

        scheduler.add_job(
            send_kite_login_alert,
            CronTrigger(day_of_week="mon-fri", hour=8, minute=45, timezone=IST),
            id="kite_morning_alert",
            name="Kite Morning Alert: Daily login link via Telegram (08:45 IST)",
        )

        # RS EMA50×200 Strategy — daily signals + position update at 16:30 IST
        from backend.intelligence.rs_ema_strategy import run_rs_ema_daily

        scheduler.add_job(
            run_rs_ema_daily,
            CronTrigger(day_of_week="mon-fri", hour=16, minute=30, timezone=IST),
            id="rs_ema_strategy",
            name="RS EMA50×200: Daily Signal Scan + Paper Trades (16:30 IST)",
        )

        # Shadow Portfolio — update exits every 30 min during market hours
        from backend.intelligence.shadow_portfolio import update_shadow_exits

        scheduler.add_job(
            update_shadow_exits,
            CronTrigger(day_of_week="mon-fri", hour="9-16", minute="15,45", timezone=IST),
            id="shadow_portfolio",
            name="Shadow Portfolio: Exit Tracker",
        )

        # ── v2 validated daily pipeline (paper-live) ─────────────────────
        # Order mirrors the backtest's per-day loop (exit → entry → scan):
        #   17:30 ingest — Kite adjusted bars → bar store
        #   17:40 EXIT   — close-based 5×ATR chandelier on open trades
        #   17:45 ENTRY  — fill breakouts of yesterday's READY watchlist
        #   17:50 SCAN   — v2 SETUP scan → ScanResult → watchlist for tomorrow
        #   09:15 GAP    — exit any position that gaps open below its stop
        from backend.services.live_jobs import (
            run_daily_ingest,
            run_daily_scan,
            run_entry_pass,
            run_exit_pass,
            run_morning_gap_pass,
        )

        scheduler.add_job(
            run_daily_ingest,
            CronTrigger(day_of_week="mon-fri", hour=17, minute=30, timezone=IST),
            id="kite_ingest",
            name="v2 Ingest: Kite adjusted bars -> store (17:30 IST)",
        )
        scheduler.add_job(
            run_exit_pass,
            CronTrigger(day_of_week="mon-fri", hour=17, minute=40, timezone=IST),
            id="exit_monitor",
            name="v2 Exit: post-close close-based chandelier stop (17:40 IST)",
        )
        scheduler.add_job(
            run_entry_pass,
            CronTrigger(day_of_week="mon-fri", hour=17, minute=45, timezone=IST),
            id="entry_monitor",
            name="v2 Entry: post-close breakout fills (17:45 IST)",
        )
        scheduler.add_job(
            run_daily_scan,
            CronTrigger(day_of_week="mon-fri", hour=17, minute=50, timezone=IST),
            id="daily_scanner",
            name="v2 Scanner: post-close SETUP scan -> watchlist (17:50 IST)",
        )
        scheduler.add_job(
            run_morning_gap_pass,
            CronTrigger(day_of_week="mon-fri", hour=9, minute=15, timezone=IST),
            id="morning_gap",
            name="v2 Exit: 09:15 gap-down check",
        )

        logger.info(f"APScheduler configured with {len(scheduler.get_jobs())} jobs")
        return scheduler

    except ImportError as e:
        logger.warning(f"APScheduler not available — intelligence jobs disabled: {e}")
        return None


# ── Lifespan ─────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup, start scheduler."""
    init_db()
    logger.info("Database initialized")

    sched = _setup_scheduler()
    if sched:
        sched.start()
        logger.info("APScheduler started — v2 pipeline active")

    yield

    if sched and sched.running:
        sched.shutdown(wait=False)
        logger.info("APScheduler shut down")


# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Champion Trader System",
    description="v2 validated swing trading pipeline — Kite data, chandelier exits, RS EMA paper trading",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(DecimalFixMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v2 pipeline routers
app.include_router(scanner.router)
app.include_router(watchlist.router)
app.include_router(trades.router)
app.include_router(journal.router)

# Intelligence + strategy
app.include_router(intelligence_router)
app.include_router(intelligence_strategy_router)
app.include_router(rs_strategy_router)

# Kite OAuth callback
app.include_router(kite_auth_router)


@app.get("/")
def root():
    return {
        "name": "Champion Trader System",
        "version": "2.0.0",
        "environment": settings.environment,
    }


@app.get("/health")
def health_check():
    import pytz

    ist = pytz.timezone("Asia/Kolkata")
    jobs = []
    if scheduler and scheduler.running:
        for j in scheduler.get_jobs():
            nxt = j.next_run_time
            if nxt:
                nxt_ist = nxt.astimezone(ist)
                next_str = nxt_ist.strftime("%Y-%m-%d %I:%M %p IST")
            else:
                next_str = "paused"
            jobs.append({"id": j.id, "name": j.name, "next_run": next_str})
    return {
        "status": "ok",
        "scheduler": "running" if scheduler and scheduler.running else "stopped",
        "scheduled_jobs": len(jobs),
        "jobs": jobs,
    }
