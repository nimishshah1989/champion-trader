"""
autooptimize.py -- The Karpathy AutoOptimize Loop for CTS.

Runs nightly (6 PM - 8 AM IST) as a background process.
Each experiment cycle:
  1. Read strategy.md for mandate and constraints
  2. Read results.tsv for experiment history
  3. Form a hypothesis (which parameter to change, in which direction, why)
  4. Modify exactly ONE value in PARAMETERS dict in strategy.py
  5. Run 90-calendar-day (~60 trading day) backtest via backtest_engine
  6. Compare composite_score to current best
  7. Git commit if improved / revert strategy.py if not
  8. Append record to results.tsv
  9. REPEAT -- NEVER STOP until manually interrupted or halt_hour reached
"""

from __future__ import annotations

import csv
import importlib
import json
import logging
import math
import re
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import git
from anthropic import Anthropic

from backend.config import settings
from backend.database import (
    OptimizeExperiment,
    SessionLocal,
    SimulationRun,
    SimulationTrade,
)
from backend.intelligence.strategy import BOUNDS, PARAMETERS, validate_parameters
from backend.services.backtest_engine import run_backtest as _bt_run_backtest

logger = logging.getLogger("autooptimize")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_FILE = PROJECT_ROOT / "backend" / "intelligence" / "strategy.py"
STRATEGY_MD = PROJECT_ROOT / "strategy.md"
RESULTS_TSV = PROJECT_ROOT / "results.tsv"
LOG_DIR = PROJECT_ROOT / "logs"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BACKTEST_WINDOW_CALENDAR_DAYS = 90       # ~60 trading days
BACKTEST_STARTING_CAPITAL = 1_000_000.0  # 10 lakh INR
BACKTEST_RPT_PCT = 0.50                  # default RPT
BACKTEST_POLL_INTERVAL_SEC = 5           # seconds between completion polls
BACKTEST_MAX_WAIT_SEC = 600              # 10 min max wait per backtest
MIN_TRADE_COUNT = 8                      # below this, composite_score = 0
MAX_DRAWDOWN_PENALTY_THRESHOLD = 0.15    # halve score above 15% drawdown
EXPERIMENT_HISTORY_WINDOW = 20           # last N experiments shown to Claude
PAUSE_ON_ERROR_SEC = 30                  # pause before retrying after error

# Integer-valued parameters (written without decimal point)
INTEGER_PARAMETERS = frozenset({
    "contraction_atr_lookback",
    "contraction_narrowing_min",
    "min_base_days",
    "sma_window",
    "stage_sma_lookback",
})

# ---------------------------------------------------------------------------
# Thread control
# ---------------------------------------------------------------------------

_stop_event = threading.Event()
_running = False
_last_result: dict[str, Any] | None = None


# ===========================================================================
# 1. COMPOSITE SCORE
# ===========================================================================

def compute_composite_score(run: SimulationRun, trades: list[SimulationTrade]) -> dict:
    """
    Compute the composite score from a completed backtest run.

    composite_score = expectancy * sqrt(trade_count) * (1 - max_drawdown_pct)

    where:
      expectancy = (win_rate * avg_win_R) - (loss_rate * avg_loss_R)
      PENALTY: score halved if max_drawdown > 15%
      PENALTY: score = 0 if trade_count < MIN_TRADE_COUNT
    """
    trade_count = len(trades)

    if trade_count < MIN_TRADE_COUNT:
        return {
            "composite_score": 0.0,
            "expectancy": 0.0,
            "trade_count": trade_count,
            "max_drawdown_pct": run.max_drawdown_pct or 0.0,
            "win_rate": 0.0,
        }

    wins = [t for t in trades if (t.r_multiple or 0) > 0]
    losses = [t for t in trades if (t.r_multiple or 0) <= 0]

    win_rate = len(wins) / trade_count
    loss_rate = 1.0 - win_rate

    avg_win_r = (
        sum(t.r_multiple for t in wins if t.r_multiple is not None) / len(wins)
        if wins
        else 0.0
    )
    avg_loss_r = (
        abs(sum(t.r_multiple for t in losses if t.r_multiple is not None) / len(losses))
        if losses
        else 0.0
    )

    expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)

    # max_drawdown_pct from backtest_engine is stored as percentage (0-100)
    raw_dd = run.max_drawdown_pct or 0.0
    max_dd = raw_dd / 100.0 if raw_dd > 1.0 else raw_dd

    score = expectancy * math.sqrt(trade_count) * (1.0 - max_dd)

    if max_dd > MAX_DRAWDOWN_PENALTY_THRESHOLD:
        score *= 0.5

    return {
        "composite_score": round(score, 6),
        "expectancy": round(expectancy, 4),
        "trade_count": trade_count,
        "max_drawdown_pct": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
    }


# ===========================================================================
# 2. BACKTEST ADAPTER
# ===========================================================================

def _wait_for_backtest(run_id: int, timeout_sec: int = BACKTEST_MAX_WAIT_SEC) -> SimulationRun:
    """
    Poll the database until the backtest run reaches COMPLETED or FAILED.
    The backtest_engine runs in a background thread, so we poll.
    Returns the refreshed SimulationRun row.
    Raises RuntimeError on timeout or failure.
    """
    elapsed = 0
    while elapsed < timeout_sec:
        db = SessionLocal()
        try:
            run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
            if run is None:
                raise RuntimeError(f"Backtest run {run_id} not found in database")
            if run.status == "COMPLETED":
                return run
            if run.status == "FAILED":
                raise RuntimeError(
                    f"Backtest run {run_id} failed: {run.error_message or 'unknown error'}"
                )
        finally:
            db.close()

        time.sleep(BACKTEST_POLL_INTERVAL_SEC)
        elapsed += BACKTEST_POLL_INTERVAL_SEC

    raise RuntimeError(f"Backtest run {run_id} timed out after {timeout_sec}s")


def _run_backtest_and_score() -> tuple[float, dict]:
    """
    Launch a backtest for the standard window, wait for completion,
    and return (composite_score, full_metrics_dict).
    """
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=BACKTEST_WINDOW_CALENDAR_DAYS)

    db = SessionLocal()
    try:
        sim_run = _bt_run_backtest(
            db=db,
            start_date=start_dt,
            end_date=end_dt,
            starting_capital=BACKTEST_STARTING_CAPITAL,
            rpt_pct=BACKTEST_RPT_PCT,
            name=f"autooptimize_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
        run_id = sim_run.id
    finally:
        db.close()

    # Poll until complete
    completed_run = _wait_for_backtest(run_id)

    # Fetch trades for scoring
    db = SessionLocal()
    try:
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        trades = (
            db.query(SimulationTrade)
            .filter(SimulationTrade.run_id == run_id)
            .all()
        )
        metrics = compute_composite_score(run, trades)
    finally:
        db.close()

    return metrics["composite_score"], metrics


# ===========================================================================
# 3. RESULTS.TSV I/O
# ===========================================================================

_TSV_FIELDS = [
    "timestamp",
    "parameter",
    "old_value",
    "new_value",
    "hypothesis",
    "old_score",
    "new_score",
    "outcome",
    "trade_count",
    "expectancy",
    "max_dd",
]


def _read_last_n_results(n: int = EXPERIMENT_HISTORY_WINDOW) -> str:
    """Read last N rows from results.tsv as a formatted string for Claude."""
    if not RESULTS_TSV.exists():
        return "No previous experiments."

    lines = RESULTS_TSV.read_text().strip().split("\n")
    if len(lines) <= 1:
        return "No previous experiments. You are the first researcher."

    header = lines[0]
    data_lines = lines[1:]
    recent = data_lines[-n:] if len(data_lines) > n else data_lines
    return header + "\n" + "\n".join(recent)


def _append_results_tsv(record: dict) -> None:
    """Append a single experiment record to results.tsv."""
    file_exists = RESULTS_TSV.exists() and RESULTS_TSV.stat().st_size > 0

    with open(RESULTS_TSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_TSV_FIELDS, delimiter="\t")
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in _TSV_FIELDS})


# ===========================================================================
# 4. DATABASE LOGGING
# ===========================================================================

def _log_to_db(record: dict) -> None:
    """Persist experiment record to the optimize_experiments table."""
    db = SessionLocal()
    try:
        experiment = OptimizeExperiment(
            run_date=date.today(),
            parameter_name=record["parameter"],
            old_value=record["old_value"],
            new_value=record["new_value"],
            hypothesis=record["hypothesis"],
            old_score=record["old_score"],
            new_score=record["new_score"],
            outcome=record["outcome"],
            trade_count=record["trade_count"],
            expectancy=record["expectancy"],
            max_drawdown_pct=record["max_dd"],
        )
        db.add(experiment)
        db.commit()
    except Exception as exc:
        logger.error(f"Failed to log experiment to DB: {exc}")
        db.rollback()
    finally:
        db.close()


# ===========================================================================
# 5. STRATEGY FILE MUTATION
# ===========================================================================

def _modify_strategy_file(parameter: str, new_value: float) -> float:
    """
    Modify exactly one parameter in strategy.py's PARAMETERS dict.
    Returns the old value.
    Raises ValueError if the parameter cannot be found or is out of bounds.
    """
    if parameter not in BOUNDS:
        raise ValueError(f"Unknown parameter: {parameter}")

    lo, hi = BOUNDS[parameter]
    if not (lo <= new_value <= hi):
        raise ValueError(f"{parameter}={new_value} outside bounds [{lo}, {hi}]")

    old_value = PARAMETERS[parameter]
    content = STRATEGY_FILE.read_text()

    # Match pattern:  "parameter_name": <optional spaces> <number>,
    # The number can be int or float: 1.5, 0.60, 20, 150
    pattern = rf'("{re.escape(parameter)}":\s*)([\d]+(?:\.[\d]+)?)'

    # Format the new value: integers stay integers, floats keep precision
    if parameter in INTEGER_PARAMETERS:
        new_val_str = str(int(new_value))
    else:
        # Preserve 2 decimal places for float parameters
        new_val_str = f"{new_value:.2f}"

    new_content, sub_count = re.subn(pattern, rf"\g<1>{new_val_str}", content)

    if sub_count == 0:
        raise ValueError(
            f"Failed to locate parameter '{parameter}' in {STRATEGY_FILE}"
        )

    STRATEGY_FILE.write_text(new_content)

    # Reload the strategy module so PARAMETERS dict reflects the new value
    import backend.intelligence.strategy as strat_module

    importlib.reload(strat_module)
    PARAMETERS.update(strat_module.PARAMETERS)

    logger.info(f"Modified {parameter}: {old_value} -> {new_value}")
    return old_value


def _revert_strategy_file(parameter: str, old_value: float) -> None:
    """Revert a parameter to its previous value."""
    _modify_strategy_file(parameter, old_value)
    logger.info(f"Reverted {parameter} back to {old_value}")


# ===========================================================================
# 6. CLAUDE HYPOTHESIS GENERATION
# ===========================================================================

_HYPOTHESIS_SYSTEM_PROMPT = (
    "You are an autonomous trading parameter researcher. "
    "You analyze experiment history and form data-driven hypotheses. "
    "Respond ONLY with valid JSON. No markdown, no explanation outside the JSON."
)

_HYPOTHESIS_USER_TEMPLATE = """## Research Mandate
{mandate}

## Current Parameters
{params_json}

## Parameter Bounds (hard walls -- you must NOT exceed these)
{bounds_json}

## Experiment History (most recent {history_window})
{results_history}

## Your Task
Based on the experiment history and current parameters, form a hypothesis about
which SINGLE parameter to change and what new value to try.

Respond with EXACTLY this JSON format, nothing else:
{{"parameter": "<parameter_name>", "new_value": <number>, "hypothesis": "<one sentence explaining your reasoning>"}}

Rules:
- Change exactly ONE parameter per experiment
- The new_value MUST be strictly within the bounds for that parameter
- Base your hypothesis on patterns in the experiment history
- If no history exists, start with PPC signal thresholds (they drive most trade generation)
- Avoid repeating an experiment that already showed REVERT with the same direction
- Consider trade-offs: tighter filters reduce false signals but also reduce trade_count
- Weight parameters must respect the constraint: weight_ppc + weight_contraction + weight_npc_filter = 1.0
  If you change one weight, the others will need adjustment in future experiments"""


def _get_hypothesis_from_claude(
    current_params: dict[str, float],
    results_history: str,
    mandate: str,
) -> dict[str, Any]:
    """
    Call Claude to form a hypothesis about which parameter to change.

    Returns: {"parameter": str, "new_value": float, "hypothesis": str}
    Raises: ValueError if Claude returns invalid/out-of-bounds suggestions.
    """
    client = Anthropic(api_key=settings.anthropic_api_key)

    params_json = json.dumps(current_params, indent=2)
    bounds_json = json.dumps(
        {k: [v[0], v[1]] for k, v in BOUNDS.items()}, indent=2
    )

    user_content = _HYPOTHESIS_USER_TEMPLATE.format(
        mandate=mandate,
        params_json=params_json,
        bounds_json=bounds_json,
        results_history=results_history,
        history_window=EXPERIMENT_HISTORY_WINDOW,
    )

    response = client.messages.create(
        model=settings.autooptimize_model,
        max_tokens=1024,
        system=_HYPOTHESIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw_text = response.content[0].text.strip()

    # Handle markdown code blocks that Claude sometimes wraps JSON in
    code_block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
    text = code_block_match.group(1) if code_block_match else raw_text

    parsed = json.loads(text)

    param_name = str(parsed["parameter"])
    new_val = float(parsed["new_value"])
    hypothesis_text = str(parsed.get("hypothesis", "No hypothesis provided"))

    # Validate parameter exists
    if param_name not in BOUNDS:
        raise ValueError(f"Claude suggested unknown parameter: {param_name}")

    # Validate bounds
    lo, hi = BOUNDS[param_name]
    if not (lo <= new_val <= hi):
        raise ValueError(
            f"Claude suggested {param_name}={new_val}, outside bounds [{lo}, {hi}]"
        )

    # Validate weight constraint if touching a weight parameter
    weight_keys = {"weight_ppc", "weight_contraction", "weight_npc_filter"}
    if param_name in weight_keys:
        test_params = dict(current_params)
        test_params[param_name] = new_val
        weight_sum = sum(test_params[k] for k in weight_keys)
        if abs(weight_sum - 1.0) > 0.01:
            raise ValueError(
                f"Changing {param_name} to {new_val} would make weights sum "
                f"to {weight_sum:.3f} (must be ~1.0). Rejecting hypothesis."
            )

    return {
        "parameter": param_name,
        "new_value": new_val,
        "hypothesis": hypothesis_text,
    }


# ===========================================================================
# 7. GIT OPERATIONS
# ===========================================================================

def _git_commit_improvement(
    parameter: str,
    old_value: float,
    new_value: float,
    old_score: float,
    new_score: float,
) -> bool:
    """
    Git-add strategy.py and commit with a descriptive message.
    Returns True on success, False on failure.
    """
    try:
        repo = git.Repo(PROJECT_ROOT)
        relative_path = str(STRATEGY_FILE.relative_to(PROJECT_ROOT))
        repo.index.add([relative_path])
        repo.index.commit(
            f"autooptimize: {parameter} {old_value}->{new_value} "
            f"(score {old_score:.4f}->{new_score:.4f})"
        )
        logger.info(f"Git commit: {parameter} improvement committed")
        return True
    except Exception as exc:
        logger.warning(f"Git commit failed (non-fatal): {exc}")
        return False


# ===========================================================================
# 8. SINGLE EXPERIMENT CYCLE
# ===========================================================================

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

    Returns a record dict with keys matching _TSV_FIELDS plus "outcome".
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
    history = _read_last_n_results(EXPERIMENT_HISTORY_WINDOW)

    # --- 3. Snapshot current params ---
    current_params = dict(PARAMETERS)

    # --- 4. Establish baseline ---
    if baseline_score is None:
        logger.info("Running baseline backtest (no prior score)...")
        baseline_score, baseline_metrics = _run_backtest_and_score()
        logger.info(
            f"Baseline: score={baseline_score:.4f}, "
            f"trades={baseline_metrics['trade_count']}, "
            f"expectancy={baseline_metrics['expectancy']:.4f}"
        )

    # --- 5. Get hypothesis from Claude ---
    hypothesis = _get_hypothesis_from_claude(current_params, history, mandate)
    param_name = hypothesis["parameter"]
    new_value = hypothesis["new_value"]
    hypothesis_text = hypothesis["hypothesis"]

    logger.info(
        f"Hypothesis: {param_name} -> {new_value} | {hypothesis_text}"
    )

    # --- 6. Modify strategy.py ---
    old_value = _modify_strategy_file(param_name, new_value)

    # --- 7. Run backtest with modified parameter ---
    try:
        new_score, new_metrics = _run_backtest_and_score()
    except Exception as exc:
        logger.error(f"Backtest with modified param failed: {exc}")
        _revert_strategy_file(param_name, old_value)
        error_record = {
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
        _append_results_tsv(error_record)
        _log_to_db(error_record)
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
        _git_commit_improvement(
            param_name, old_value, new_value, baseline_score, new_score
        )
    else:
        outcome = "REVERT"
        logger.info(
            f"NO IMPROVEMENT: {baseline_score:.4f} -> {new_score:.4f}. "
            f"Reverting {param_name} to {old_value}."
        )
        _revert_strategy_file(param_name, old_value)

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
    _append_results_tsv(record)
    _log_to_db(record)

    _last_result = record
    return record


# ===========================================================================
# 9. MAIN LOOP
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
    logger.info(f"Strategy file: {STRATEGY_FILE}")
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
# 10. STATUS & HISTORY
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
        "strategy_file": str(STRATEGY_FILE),
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
