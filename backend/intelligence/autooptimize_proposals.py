"""
autooptimize_proposals.py -- Parameter proposal generation and hypothesis creation.

Uses Claude API to form data-driven hypotheses about which single parameter
to change in the CTS strategy, then mutates strategy.py accordingly.
Also handles results.tsv I/O, database logging, and git operations.
"""

from __future__ import annotations

import csv
import importlib
import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import git
from anthropic import Anthropic

from backend.config import settings
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
# CLAUDE HYPOTHESIS GENERATION
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


def get_hypothesis_from_claude(
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
