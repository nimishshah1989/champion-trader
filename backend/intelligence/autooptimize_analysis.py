"""
autooptimize_analysis.py -- Post-session Claude analysis.

Called ONCE per AutoOptimize session (after all experiments complete).
Reads the full experiment history, sends ONE Claude API call to get
strategic insights on what's working and what to try next.

Cost: ~$0.10/call × 1 call/night = ~$3/month.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import settings
from backend.intelligence.autooptimize_proposals import (
    read_last_n_results,
    RESULTS_TSV,
)
from backend.intelligence.strategy import PARAMETERS, BOUNDS

logger = logging.getLogger("autooptimize")

_ANALYSIS_SYSTEM = (
    "You are a trading parameter research analyst. "
    "Analyze experiment results and provide strategic insights. "
    "Respond with valid JSON only."
)

_ANALYSIS_TEMPLATE = """## Session Summary
Experiments run: {experiment_count}
Kept (improved): {keep_count}
Reverted: {revert_count}

## Current Parameters
{params_json}

## Recent Experiment History
{results_history}

## Your Task
Analyze the experiment results and provide:
1. Which parameters are showing the most promise for improvement
2. Which parameter ranges seem optimal based on the data
3. What to try in the next session (2-3 specific suggestions)

Respond with this JSON:
{{"analysis": "<2-3 sentence summary>", "promising_params": ["param1", "param2"], "next_suggestions": ["suggestion1", "suggestion2"]}}"""


def run_session_analysis(
    experiment_count: int,
    keep_count: int,
    revert_count: int,
) -> dict[str, Any]:
    """
    Run ONE Claude API call to analyze the full session's experiment results.

    Returns structured analysis dict. Falls back to rule-based summary on error.
    """
    try:
        from anthropic import Anthropic

        if not settings.anthropic_api_key:
            return _fallback_analysis(experiment_count, keep_count, revert_count)

        client = Anthropic(api_key=settings.anthropic_api_key)

        history = read_last_n_results(30)
        params_json = json.dumps(dict(PARAMETERS), indent=2)

        user_content = _ANALYSIS_TEMPLATE.format(
            experiment_count=experiment_count,
            keep_count=keep_count,
            revert_count=revert_count,
            params_json=params_json,
            results_history=history,
        )

        response = client.messages.create(
            model=settings.autooptimize_model,
            max_tokens=512,
            system=_ANALYSIS_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = response.content[0].text.strip()

        # Try to parse JSON
        import re
        code_block = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
        text = code_block.group(1) if code_block else raw_text

        result = json.loads(text)
        result["source"] = "claude"

        # Log the analysis to file for future reference
        _save_analysis(result, experiment_count, keep_count, revert_count)

        return result

    except Exception as exc:
        logger.warning(f"Claude analysis failed, using fallback: {exc}")
        return _fallback_analysis(experiment_count, keep_count, revert_count)


def _fallback_analysis(
    experiment_count: int,
    keep_count: int,
    revert_count: int,
) -> dict[str, Any]:
    """Rule-based analysis when Claude is unavailable."""
    keep_rate = keep_count / max(experiment_count, 1)

    if keep_rate > 0.5:
        analysis = "Strong session — over half of experiments improved the score. Parameters are converging."
    elif keep_rate > 0.2:
        analysis = "Moderate session — some improvements found. Continue exploring nearby parameter space."
    else:
        analysis = "Challenging session — few improvements. Consider widening search range or different parameters."

    return {
        "analysis": analysis,
        "keep_rate": round(keep_rate, 2),
        "source": "fallback",
    }


def _save_analysis(
    result: dict[str, Any],
    experiment_count: int,
    keep_count: int,
    revert_count: int,
) -> None:
    """Save analysis to a log file for future reference."""
    from datetime import datetime

    log_dir = RESULTS_TSV.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    analysis_file = log_dir / "session_analyses.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "experiments": experiment_count,
        "keeps": keep_count,
        "reverts": revert_count,
        **result,
    }

    with open(analysis_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
