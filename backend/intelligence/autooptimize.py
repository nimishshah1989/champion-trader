"""
autooptimize.py -- Main loop control, start/stop, get_status, get_history.

Scoring logic: autooptimize_scoring.py
Proposals & file mutation: autooptimize_proposals.py
"""

from __future__ import annotations

import csv
import logging
import threading
import time
from datetime import datetime
from typing import Any

from backend.config import settings
from backend.intelligence.autooptimize_proposals import (
    EXPERIMENT_HISTORY_WINDOW,
    RESULTS_TSV,
    STRATEGY_MD,
    append_results_tsv,
    get_hypothesis_from_claude,
    git_commit_improvement,
    log_to_db,
    modify_strategy_file,
    read_last_n_results,
    revert_strategy_file,
)
from backend.intelligence.autooptimize_scoring import (
    run_backtest_and_score,
)
from backend.intelligence.strategy import PARAMETERS, validate_parameters

logger = logging.getLogger("autooptimize")

LOG_DIR = RESULTS_TSV.parent / "logs"
PAUSE_ON_ERROR_SEC = 30  # pause before retrying after error
MAX_EXPERIMENTS_PER_SESSION = 10  # cap to limit compute (backtests are expensive)

_stop_event = threading.Event()
_running = False
_last_result: dict[str, Any] | None = None

def run_single_experiment(
    baseline_score: float | None = None,
) -> dict[str, Any]:
    """
    Run a single AutoOptimize experiment cycle (synchronous).

    1. Establish baseline score if not provided
    2. Ask Claude for a hypothesis
    3. Modify strategy.py
    4. Run backtest
    5. Compare scores
    6. Keep (git commit) or revert
    7. Log everywhere

    Returns a record dict with keys matching TSV fields plus "outcome".
    """
    global _last_result

    timestamp = datetime.now().isoformat()

    # --- 1. Read mandate ---
    mandate = (
        STRATEGY_MD.read_text()
        if STRATEGY_MD.exists()
        else "Maximise composite_score = expectancy * sqrt(trade_count) * (1 - max_dd)."
    )

    # --- 2. Read experiment history ---
    history = read_last_n_results(EXPERIMENT_HISTORY_WINDOW)

    # --- 3. Snapshot current params ---
    current_params = dict(PARAMETERS)

    # --- 4. Establish baseline ---
    if baseline_score is None:
        logger.info("Running baseline backtest (no prior score)...")
        baseline_score, baseline_metrics = run_backtest_and_score()
        logger.info(
            f"Baseline: score={baseline_score:.4f}, "
            f"trades={baseline_metrics['trade_count']}, "
            f"expectancy={baseline_metrics['expectancy']:.4f}"
        )

    # --- 5. Get hypothesis from Claude ---
    hypothesis = get_hypothesis_from_claude(current_params, history, mandate)
    param_name = hypothesis["parameter"]
    new_value = hypothesis["new_value"]
    hypothesis_text = hypothesis["hypothesis"]

    logger.info(
        f"Hypothesis: {param_name} -> {new_value} | {hypothesis_text}"
    )

    # --- 6. Modify strategy.py ---
    old_value = modify_strategy_file(param_name, new_value)

    # --- 7. Run backtest with modified parameter ---
    try:
        new_score, new_metrics = run_backtest_and_score()
    except Exception as exc:
        logger.error(f"Backtest with modified param failed: {exc}")
        revert_strategy_file(param_name, old_value)
        error_record: dict[str, Any] = {
            "timestamp": timestamp,
            "parameter": param_name,
            "old_value": old_value,
            "new_value": new_value,
            "hypothesis": hypothesis_text,
            "old_score": baseline_score,
            "new_score": 0.0,
            "outcome": "ERROR",
            "trade_count": 0,
            "expectancy": 0.0,
            "max_dd": 0.0,
        }
        append_results_tsv(error_record)
        log_to_db(error_record)
        _last_result = error_record
        return error_record

    # --- 8. Compare and decide ---
    if new_score > baseline_score:
        outcome = "KEEP"
        delta = new_score - baseline_score
        logger.info(
            f"IMPROVEMENT: {baseline_score:.4f} -> {new_score:.4f} "
            f"(+{delta:.4f}). Keeping change."
        )
        git_commit_improvement(
            param_name, old_value, new_value, baseline_score, new_score
        )
    else:
        outcome = "REVERT"
        logger.info(
            f"NO IMPROVEMENT: {baseline_score:.4f} -> {new_score:.4f}. "
            f"Reverting {param_name} to {old_value}."
        )
        revert_strategy_file(param_name, old_value)

    # --- 9. Build record ---
    record: dict[str, Any] = {
        "timestamp": timestamp,
        "parameter": param_name,
        "old_value": old_value,
        "new_value": new_value,
        "hypothesis": hypothesis_text,
        "old_score": round(baseline_score, 6),
        "new_score": round(new_score, 6),
        "outcome": outcome,
        "trade_count": new_metrics["trade_count"],
        "expectancy": new_metrics["expectancy"],
        "max_dd": new_metrics["max_drawdown_pct"],
    }

    # --- 10. Log everywhere ---
    append_results_tsv(record)
    log_to_db(record)

    _last_result = record
    return record


# ===========================================================================
# MAIN LOOP
# ===========================================================================

def _is_within_operating_hours() -> bool:
    """
    Check if current time is within the autooptimize operating window.

    start_hour=18 (6 PM), halt_hour=8 (8 AM) means:
      - Run from 18:00 through midnight to 07:59
      - Do NOT run from 08:00 to 17:59
    """
    now_hour = datetime.now().hour
    start_hour = settings.autooptimize_start_hour
    halt_hour = settings.autooptimize_halt_hour

    if halt_hour < start_hour:
        # Overnight window: valid if hour >= start OR hour < halt
        return now_hour >= start_hour or now_hour < halt_hour
    else:
        # Same-day window: valid if start <= hour < halt
        return start_hour <= now_hour < halt_hour


def start_loop() -> None:
    """
    Start the AutoOptimize loop. Runs until stop_loop() is called
    or until autooptimize_halt_hour is reached.

    This is a blocking function -- call from a background thread or
    use start_loop_background() for non-blocking operation.
    """
    global _running

    if _running:
        logger.warning("AutoOptimize loop already running. Ignoring start request.")
        return

    _running = True
    _stop_event.clear()

    # Set up file logging for this session
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"autooptimize_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

    logger.info("=" * 60)
    logger.info("AutoOptimize loop STARTED")
    logger.info(f"Operating window: {settings.autooptimize_start_hour}:00 - {settings.autooptimize_halt_hour}:00")
    logger.info(f"Model: {settings.autooptimize_model}")
    logger.info(f"Results file: {RESULTS_TSV}")
    logger.info("=" * 60)

    experiment_count = 0
    keep_count = 0
    revert_count = 0
    error_count = 0
    current_best_score: float | None = None

    try:
        while not _stop_event.is_set():
            # Check operating hours
            if not _is_within_operating_hours():
                logger.info(
                    f"Outside operating hours ({settings.autooptimize_start_hour}:00"
                    f"-{settings.autooptimize_halt_hour}:00). Stopping loop."
                )
                break

            # Check experiment cap
            if experiment_count >= MAX_EXPERIMENTS_PER_SESSION:
                logger.info(
                    f"Experiment cap ({MAX_EXPERIMENTS_PER_SESSION}) reached. "
                    f"Stopping loop to conserve compute."
                )
                break

            # Validate parameters before each experiment
            violations = validate_parameters()
            if violations:
                logger.error(
                    f"Parameter validation failed before experiment: {violations}. "
                    f"Pausing {PAUSE_ON_ERROR_SEC}s."
                )
                time.sleep(PAUSE_ON_ERROR_SEC)
                continue

            # Run experiment
            experiment_count += 1
            logger.info(f"--- Experiment #{experiment_count} ---")

            try:
                result = run_single_experiment(baseline_score=current_best_score)
                outcome = result.get("outcome", "ERROR")

                if outcome == "KEEP":
                    current_best_score = result["new_score"]
                    keep_count += 1
                elif outcome == "REVERT":
                    # Set baseline from old_score if we have not established one
                    if current_best_score is None:
                        current_best_score = result["old_score"]
                    revert_count += 1
                elif outcome == "ERROR":
                    if current_best_score is None and "old_score" in result:
                        current_best_score = result["old_score"]
                    error_count += 1
                    time.sleep(PAUSE_ON_ERROR_SEC)

                logger.info(
                    f"Experiment #{experiment_count} -> {outcome} | "
                    f"Running total: {keep_count} KEEP, {revert_count} REVERT, "
                    f"{error_count} ERROR | Best score: {current_best_score}"
                )

            except Exception as exc:
                error_count += 1
                logger.error(
                    f"Experiment #{experiment_count} unhandled exception: {exc}",
                    exc_info=True,
                )
                time.sleep(PAUSE_ON_ERROR_SEC)

    finally:
        _running = False

        # Run Claude analysis on the full session results (one API call)
        if experiment_count > 0:
            try:
                from backend.intelligence.autooptimize_analysis import (
                    run_session_analysis,
                )
                analysis = run_session_analysis(experiment_count, keep_count, revert_count)
                logger.info(f"Claude session analysis: {analysis}")
            except Exception as exc:
                logger.warning(f"Session analysis skipped: {exc}")

        logger.info("=" * 60)
        logger.info(
            f"AutoOptimize loop STOPPED after {experiment_count} experiments. "
            f"KEEP={keep_count}, REVERT={revert_count}, ERROR={error_count}. "
            f"Final best score: {current_best_score}"
        )
        logger.info("=" * 60)
        logger.removeHandler(file_handler)
        file_handler.close()


def start_loop_background() -> threading.Thread:
    """
    Start the AutoOptimize loop in a daemon background thread.
    Returns the thread handle.
    """
    thread = threading.Thread(target=start_loop, daemon=True, name="autooptimize-loop")
    thread.start()
    logger.info("AutoOptimize background thread started")
    return thread


def stop_loop() -> None:
    """Signal the AutoOptimize loop to stop after the current experiment."""
    global _running
    _stop_event.set()
    _running = False
    logger.info("AutoOptimize loop stop requested")


# ===========================================================================
# STATUS & HISTORY
# ===========================================================================

def get_status() -> dict[str, Any]:
    """Get current AutoOptimize status for the API."""
    return {
        "running": _running,
        "enabled": settings.autooptimize_enabled,
        "model": settings.autooptimize_model,
        "operating_window": f"{settings.autooptimize_start_hour}:00-{settings.autooptimize_halt_hour}:00",
        "within_operating_hours": _is_within_operating_hours(),
        "last_result": _last_result,
        "results_file": str(RESULTS_TSV),
        "current_parameters": dict(PARAMETERS),
        "parameter_violations": validate_parameters(),
    }


def get_history() -> list[dict[str, str]]:
    """Read all results.tsv rows as a list of dicts."""
    if not RESULTS_TSV.exists():
        return []

    with open(RESULTS_TSV, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)


def get_history_summary() -> dict[str, Any]:
    """Return aggregated stats from experiment history."""
    rows = get_history()
    if not rows:
        return {"total_experiments": 0}

    keep_count = sum(1 for r in rows if r.get("outcome") == "KEEP")
    revert_count = sum(1 for r in rows if r.get("outcome") == "REVERT")
    error_count = sum(1 for r in rows if r.get("outcome") == "ERROR")

    # Find the parameter that has been kept most often
    keep_params: dict[str, int] = {}
    for r in rows:
        if r.get("outcome") == "KEEP":
            p = r.get("parameter", "unknown")
            keep_params[p] = keep_params.get(p, 0) + 1

    most_improved_param = (
        max(keep_params, key=keep_params.get) if keep_params else None
    )

    scores = [
        float(r["new_score"])
        for r in rows
        if r.get("new_score") and r.get("outcome") == "KEEP"
    ]

    return {
        "total_experiments": len(rows),
        "keep_count": keep_count,
        "revert_count": revert_count,
        "error_count": error_count,
        "keep_rate_pct": round(keep_count / len(rows) * 100, 1) if rows else 0,
        "most_improved_parameter": most_improved_param,
        "best_score": max(scores) if scores else None,
        "latest_score": scores[-1] if scores else None,
        "first_experiment": rows[0].get("timestamp"),
        "latest_experiment": rows[-1].get("timestamp"),
    }
