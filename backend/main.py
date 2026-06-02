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
    actions,
    alerts,
    calculator,
    journal,
    market_stance,
    scanner,
    simulation,
    trades,
    watchlist,
)
from backend.routers.alerts_app import router as alerts_app_router
from backend.routers.intelligence import router as intelligence_router
from backend.routers.intelligence_strategy import router as intelligence_strategy_router


# ── APScheduler Setup ────────────────────────────────────────────────

scheduler = None


def _setup_scheduler():
    """Configure APScheduler with all intelligence jobs."""
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

        # Corpus Updater — daily at 17:30 IST
        from backend.intelligence.corpus_updater import ingest_daily

        scheduler.add_job(
            ingest_daily,
            CronTrigger(day_of_week="mon-fri", hour=17, minute=30, timezone=IST),
            id="corpus_updater",
            name="Corpus Updater: Market Data Ingestion",
        )

        # AutoOptimize — start at 18:00 IST (halts internally at 08:00)
        if settings.autooptimize_enabled:
            from backend.intelligence.autooptimize import start_loop

            scheduler.add_job(
                start_loop,
                CronTrigger(
                    day_of_week="mon-fri",
                    hour=settings.autooptimize_start_hour,
                    minute=0,
                    timezone=IST,
                ),
                id="autooptimize",
                name="AutoOptimize: Overnight Research Loop",
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
        # Post-close on the day's Kite-adjusted bar — the SAME feed the backtest reads —
        # so the live scan/entry/exit are parity-faithful. The order mirrors the backtest's
        # per-day loop (exit, then entry, then refresh the watchlist for tomorrow):
        #   17:30 ingest (corpus_updater)
        #   17:40 EXIT   — close-based 5xATR chandelier on open trades
        #   17:45 ENTRY  — fill breakouts of yesterday's READY watchlist on the day's bar
        #   17:50 SCAN   — v2 SETUP scan -> ScanResult -> watchlist triggers for tomorrow
        #   09:15 GAP    — exit any position that gaps open below its stop
        # Replaces the legacy yfinance scan + the 2-min intraday 2R/4R/8R/12R ladder
        # (decisions #5/#6: exit once post-close + 09:15 gap; volume gate finalised on the
        # close). In Phase-2 LIVE the ENTRY pass moves to the last 30 min on intraday ticks.
        from backend.services.live_jobs import (
            run_daily_scan,
            run_entry_pass,
            run_exit_pass,
            run_morning_gap_pass,
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

    # Start scheduler
    sched = _setup_scheduler()
    if sched:
        sched.start()
        logger.info("APScheduler started — intelligence jobs active")

    yield

    # Shutdown
    if sched and sched.running:
        sched.shutdown(wait=False)
        logger.info("APScheduler shut down")


# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Champion Trader System",
    description="Swing trading intelligence platform based on Afzal Lokhandwala's Champion Trader methodology",
    version="2.0.0",
    lifespan=lifespan,
)

# Decimal-fix middleware — must be added BEFORE CORS so it runs after CORS
app.add_middleware(DecimalFixMiddleware)

# CORS — private trading tool, allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers — v1
app.include_router(scanner.router)
app.include_router(watchlist.router)
app.include_router(calculator.router)
app.include_router(trades.router)
app.include_router(journal.router)
app.include_router(market_stance.router)
app.include_router(alerts.router)
app.include_router(alerts_app_router)
app.include_router(actions.router)
app.include_router(simulation.router)

# Register intelligence routers — v2
app.include_router(intelligence_router)
app.include_router(intelligence_strategy_router)


@app.get("/")
def root():
    return {
        "name": "Champion Trader System",
        "version": "2.0.0",
        "environment": settings.environment,
        "intelligence": True,
        "autopilot": True,
    }


@app.get("/autopilot/status")
def autopilot_status():
    """Virtual portfolio status — shows all autopilot trades and P&L."""
    from backend.services.autopilot_report import get_virtual_portfolio_summary
    return get_virtual_portfolio_summary()


@app.post("/autopilot/run-now")
def autopilot_run_now():
    """Manually trigger autopilot: populate watchlist + execute alerts."""
    from backend.services.autopilot import (
        run_post_scan_automation,
        run_post_alert_automation,
    )
    scan_result = run_post_scan_automation()
    alert_result = run_post_alert_automation()
    return {"scan_automation": scan_result, "alert_automation": alert_result}


@app.get("/autopilot/comparison")
def autopilot_comparison(days: int = 30):
    """A/B comparison: optimized params vs frozen defaults over time."""
    from backend.services.baseline_scanner import get_comparison_history
    return get_comparison_history(days)


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
