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

        # ── Daily Scanner (post-market) ──────────────────────────────────
        # Runs all three scans (PPC + NPC + Contraction) automatically at 16:00 IST.
        # Results are saved to scan_results table.
        # AUTOPILOT: After scan, auto-populates watchlist from qualifying results.

        async def _daily_scanner_job() -> None:
            """Auto-run all scans at market close, save to DB, auto-populate watchlist."""
            from datetime import date as _date

            from sqlalchemy import and_ as _and

            from backend.database import ScanResult, SessionLocal
            from backend.services.scanner_engine import run_all_scans
            from backend.services.autopilot import run_post_scan_automation

            scan_date_str = str(_date.today())
            db = SessionLocal()
            try:
                logger.info(f"[SCHEDULER] Daily scan starting for {scan_date_str}")
                results, all_data = await run_all_scans(scan_date_str)

                # Upsert — delete existing results for today, then insert fresh
                for result_dict in results:
                    db.query(ScanResult).filter(
                        _and(
                            ScanResult.scan_date == result_dict["scan_date"],
                            ScanResult.symbol == result_dict["symbol"],
                            ScanResult.scan_type == result_dict["scan_type"],
                        )
                    ).delete()
                    db.add(ScanResult(**result_dict))

                db.commit()
                logger.info(
                    f"[SCHEDULER] Daily scan complete: {len(results)} results saved for {scan_date_str}"
                )

                # AUTOPILOT: auto-populate watchlist from scan results
                auto_result = run_post_scan_automation()
                logger.info(f"[AUTOPILOT] Post-scan result: {auto_result}")

                # A/B BASELINE: run same scans with frozen default params
                from backend.services.baseline_scanner import (
                    run_baseline_scans,
                    save_and_compare,
                )
                baseline_results = run_baseline_scans(all_data, scan_date_str)
                comparison = save_and_compare(baseline_results)
                logger.info(f"[BASELINE] Comparison result: {comparison}")

            except Exception as exc:
                logger.error(f"[SCHEDULER] Daily scanner job failed: {exc}")
                db.rollback()
            finally:
                db.close()

        scheduler.add_job(
            _daily_scanner_job,
            CronTrigger(day_of_week="mon-fri", hour=16, minute=0, timezone=IST),
            id="daily_scanner",
            name="Daily Scanner: Post-Market PPC + NPC + Contraction (16:00 IST)",
        )

        # ── Live Market Monitor ───────────────────────────────────────────
        # Two jobs replace manual "Refresh Prices":
        #   1. exit_monitor  — every 2 min, full market hours → SL/target checks only
        #   2. entry_monitor — every 1 min, 15:00–15:30 IST  → trigger-break entries
        # Both write to AutoCheckLog for a full audit trail.

        from backend.database import SessionLocal
        from backend.services.price_monitor import run_price_check
        from backend.services.autopilot import run_post_alert_automation

        def _auto_check_exits() -> None:
            """Auto check open trades for SL hits and profit targets, then auto-execute."""
            db = SessionLocal()
            try:
                run_price_check(db, check_entries=False, check_exits=True, source="SCHEDULER")
            except Exception as exc:
                logger.error(f"exit_monitor job failed: {exc}")
            finally:
                db.close()
            # AUTOPILOT: auto-execute any SELL alerts generated
            try:
                result = run_post_alert_automation()
                if result.get("sells_executed", 0) > 0:
                    logger.info(f"[AUTOPILOT] Post-exit-check: {result}")
            except Exception as exc:
                logger.error(f"[AUTOPILOT] Post-exit automation failed: {exc}")

        def _auto_check_entries() -> None:
            """Auto check READY watchlist for trigger breaks, then auto-execute."""
            db = SessionLocal()
            try:
                run_price_check(db, check_entries=True, check_exits=False, source="SCHEDULER")
            except Exception as exc:
                logger.error(f"entry_monitor job failed: {exc}")
            finally:
                db.close()
            # AUTOPILOT: auto-execute any BUY alerts generated
            try:
                result = run_post_alert_automation()
                if result.get("buys_executed", 0) > 0:
                    logger.info(f"[AUTOPILOT] Post-entry-check: {result}")
            except Exception as exc:
                logger.error(f"[AUTOPILOT] Post-entry automation failed: {exc}")

        # Exit monitor: every 2 min throughout market hours (9:00–15:30 IST)
        scheduler.add_job(
            _auto_check_exits,
            CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/2", timezone=IST),
            id="exit_monitor",
            name="Live Monitor: Exit/SL Checker (every 2 min)",
        )

        # Entry monitor: every 1 min during the last 30-min entry window (15:00–15:30 IST)
        scheduler.add_job(
            _auto_check_entries,
            CronTrigger(day_of_week="mon-fri", hour="15", minute="0-30", timezone=IST),
            id="entry_monitor",
            name="Live Monitor: Entry Window Checker (every 1 min, 15:00–15:30)",
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

# Register intelligence router — v2
app.include_router(intelligence_router)


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
