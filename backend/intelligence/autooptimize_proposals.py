"""
autooptimize_proposals.py -- Parameter proposal generation and hypothesis creation.

Uses deterministic parameter sweep to form hypotheses about which single
parameter to change in the CTS strategy, then mutates strategy.py accordingly.
Also handles results.tsv I/O, database logging, and git operations.

Zero Claude API cost — all hypotheses generated via rules + random perturbation.
"""

from __future__ import annotations

import csv
import importlib
import json
import logging
import random
import re
from datetime import date
from pathlib import Path
from typing import Any

import git

from backend.database import (
    OptimizeExperiment,
    SessionLocal,
)
from backend.intelligence.strategy import BOUNDS, PARAMETERS

logger = logging.getLogger("autooptimize")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_FILE = PROJECT_ROOT / "backend" / "intelligence" / "strategy.py"
STRATEGY_MD = PROJECT_ROOT / "strategy.md"
RESULTS_TSV = PROJECT_ROOT / "results.tsv"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPERIMENT_HISTORY_WINDOW = 20  # last N experiments shown to Claude

# Integer-valued parameters (written without decimal point)
INTEGER_PARAMETERS = frozenset({
    "contraction_atr_lookback",
    "contraction_narrowing_min",
    "min_base_days",
    "sma_window",
    "stage_sma_lookback",
})


# ===========================================================================
# RESULTS.TSV I/O
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


def read_last_n_results(n: int = EXPERIMENT_HISTORY_WINDOW) -> str:
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


def append_results_tsv(record: dict[str, Any]) -> None:
    """Append a single experiment record to results.tsv."""
    file_exists = RESULTS_TSV.exists() and RESULTS_TSV.stat().st_size > 0

    with open(RESULTS_TSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_TSV_FIELDS, delimiter="\t")
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in _TSV_FIELDS})


# ===========================================================================
# DATABASE LOGGING
# ===========================================================================

def log_to_db(record: dict[str, Any]) -> None:
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
# STRATEGY FILE MUTATION
# ===========================================================================

def modify_strategy_file(parameter: str, new_value: float) -> float:
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
    pattern = rf'("{re.escape(parameter)}":\s*)([\d]+(?:\.[\d]+)?)'

    # Format the new value: integers stay integers, floats keep precision
    if parameter in INTEGER_PARAMETERS:
        new_val_str = str(int(new_value))
    else:
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


def revert_strategy_file(parameter: str, old_value: float) -> None:
    """Revert a parameter to its previous value."""
    modify_strategy_file(parameter, old_value)
    logger.info(f"Reverted {parameter} back to {old_value}")


# ===========================================================================
# DETERMINISTIC HYPOTHESIS GENERATION (zero Claude API cost)
# ===========================================================================

# Parameters to cycle through, ordered by impact on trade generation
_PARAM_PRIORITY = [
    "ppc_trp_ratio_min",
    "ppc_close_position_min",
    "ppc_volume_ratio_min",
    "min_base_days",
    "npc_trp_ratio_min",
    "npc_close_position_max",
    "npc_volume_ratio_min",
    "contraction_atr_lookback",
    "contraction_narrowing_min",
    "contraction_resistance_pct",
    "sma_window",
    "stage_sma_lookback",
    "min_adt_crore",
]

# Weight params excluded from random sweep — they need coordinated changes
_WEIGHT_PARAMS = frozenset({"weight_ppc", "weight_contraction", "weight_npc_filter"})

# Step sizes as fraction of the parameter's range
_STEP_FRACTION = 0.15


def _parse_recent_experiments(results_history: str) -> list[dict[str, str]]:
    """Parse TSV history string into list of dicts."""
    lines = results_history.strip().split("\n")
    if len(lines) <= 1:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        vals = line.split("\t")
        if len(vals) == len(header):
            rows.append(dict(zip(header, vals)))
    return rows


def get_hypothesis_from_claude(
    current_params: dict[str, float],
    results_history: str,
    mandate: str,
) -> dict[str, Any]:
    """
    Generate a deterministic hypothesis about which parameter to change.

    Uses round-robin parameter selection with random perturbation within bounds.
    Avoids repeating recently reverted experiments in the same direction.
    Zero API cost — no LLM calls.

    Returns: {"parameter": str, "new_value": float, "hypothesis": str}
    """
    recent = _parse_recent_experiments(results_history)

    # Build set of recently tried (param, direction) combos that were REVERT
    reverted: set[tuple[str, str]] = set()
    recently_tried: set[str] = set()
    for row in recent[-10:]:
        param = row.get("parameter", "")
        outcome = row.get("outcome", "")
        recently_tried.add(param)
        if outcome == "REVERT":
            old_val = float(row.get("old_value", 0))
            new_val = float(row.get("new_value", 0))
            direction = "up" if new_val > old_val else "down"
            reverted.add((param, direction))

    # Pick parameter: prefer ones not recently tried
    param_name = None
    for p in _PARAM_PRIORITY:
        if p not in recently_tried and p not in _WEIGHT_PARAMS:
            param_name = p
            break

    # If all have been tried recently, pick the one tried longest ago
    if param_name is None:
        for p in _PARAM_PRIORITY:
            if p not in _WEIGHT_PARAMS:
                param_name = p
                break

    if param_name is None:
        param_name = _PARAM_PRIORITY[0]

    current_val = current_params[param_name]
    lo, hi = BOUNDS[param_name]
    step = (hi - lo) * _STEP_FRACTION

    # Try up first, then down; skip if that direction was recently reverted
    direction = random.choice(["up", "down"])
    if (param_name, direction) in reverted:
        direction = "down" if direction == "up" else "up"

    if direction == "up":
        new_val = current_val + step * random.uniform(0.5, 1.5)
    else:
        new_val = current_val - step * random.uniform(0.5, 1.5)

    # Clamp to bounds
    new_val = max(lo, min(hi, new_val))

    # Round appropriately
    if param_name in INTEGER_PARAMETERS:
        new_val = float(round(new_val))
    else:
        new_val = round(new_val, 2)

    # Don't test the same value
    if abs(new_val - current_val) < 0.001:
        new_val = current_val + step if current_val + step <= hi else current_val - step
        new_val = max(lo, min(hi, new_val))
        if param_name in INTEGER_PARAMETERS:
            new_val = float(round(new_val))
        else:
            new_val = round(new_val, 2)

    actual_dir = "increase" if new_val > current_val else "decrease"
    hypothesis_text = (
        f"Systematic sweep: {actual_dir} {param_name} from {current_val} to {new_val} "
        f"to test impact on composite score."
    )

    return {
        "parameter": param_name,
        "new_value": new_val,
        "hypothesis": hypothesis_text,
    }


# ===========================================================================
# GIT OPERATIONS
# ===========================================================================

def git_commit_improvement(
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
