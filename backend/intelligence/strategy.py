"""
strategy.py — THE ONLY FILE THE AUTOOPTIMIZE AGENT MODIFIES.

All signal thresholds are defined here as a single PARAMETERS dict.
The AutoOptimize agent modifies exactly ONE value per experiment.
Bounds are HARD WALLS — the agent must never exceed them.

backtest_engine.py and trading_rules.py are NEVER modified.
"""

from typing import Dict, Tuple

PARAMETERS: Dict[str, float] = {
    # ── PPC Signal Thresholds ──────────────────────────────────────────
    "ppc_trp_ratio_min":          1.5,    # bounds: [1.2, 2.5]
    "ppc_close_position_min":     0.60,   # bounds: [0.50, 0.80]
    "ppc_volume_ratio_min":       1.5,    # bounds: [1.2, 2.5]

    # ── NPC Signal Thresholds ──────────────────────────────────────────
    "npc_trp_ratio_min":          1.5,    # bounds: [1.2, 2.5]
    "npc_close_position_max":     0.40,   # bounds: [0.20, 0.50]
    "npc_volume_ratio_min":       1.5,    # bounds: [1.2, 2.5]

    # ── Contraction Signal Thresholds ──────────────────────────────────
    "contraction_atr_lookback":   5,      # bounds: [3, 10]
    "contraction_narrowing_min":  3,      # bounds: [2, 5]
    "contraction_resistance_pct": 3.0,    # bounds: [2.0, 5.0]

    # ── Base & Stage Analysis ──────────────────────────────────────────
    "min_base_days":              20,     # bounds: [15, 35]
    "sma_window":                 150,    # bounds: [120, 180]
    "stage_sma_lookback":         20,     # bounds: [15, 30]

    # ── Liquidity Filter ───────────────────────────────────────────────
    "min_adt_crore":              1.0,    # bounds: [0.5, 3.0]

    # ── Composite Score Weights (must sum to 1.0) ──────────────────────
    "weight_ppc":                 0.50,   # bounds: [0.30, 0.70]
    "weight_contraction":         0.30,   # bounds: [0.20, 0.50]
    "weight_npc_filter":          0.20,   # bounds: [0.10, 0.30]
}

BOUNDS: Dict[str, Tuple[float, float]] = {
    "ppc_trp_ratio_min":          (1.2, 2.5),
    "ppc_close_position_min":     (0.50, 0.80),
    "ppc_volume_ratio_min":       (1.2, 2.5),
    "npc_trp_ratio_min":          (1.2, 2.5),
    "npc_close_position_max":     (0.20, 0.50),
    "npc_volume_ratio_min":       (1.2, 2.5),
    "contraction_atr_lookback":   (3, 10),
    "contraction_narrowing_min":  (2, 5),
    "contraction_resistance_pct": (2.0, 5.0),
    "min_base_days":              (15, 35),
    "sma_window":                 (120, 180),
    "stage_sma_lookback":         (15, 30),
    "min_adt_crore":              (0.5, 3.0),
    "weight_ppc":                 (0.30, 0.70),
    "weight_contraction":         (0.20, 0.50),
    "weight_npc_filter":          (0.10, 0.30),
}


def validate_parameters() -> list[str]:
    """Validate all PARAMETERS are within BOUNDS. Returns list of violations."""
    violations = []
    for key, value in PARAMETERS.items():
        if key not in BOUNDS:
            violations.append(f"{key}: no bounds defined")
            continue
        lo, hi = BOUNDS[key]
        if not (lo <= value <= hi):
            violations.append(f"{key}: {value} outside [{lo}, {hi}]")

    # Check weights sum to 1.0
    weight_sum = PARAMETERS["weight_ppc"] + PARAMETERS["weight_contraction"] + PARAMETERS["weight_npc_filter"]
    if abs(weight_sum - 1.0) > 0.01:
        violations.append(f"weights sum to {weight_sum}, expected 1.0")

    return violations


def get_parameter(name: str) -> float:
    """Get a parameter value by name. Raises KeyError if not found."""
    return PARAMETERS[name]


# DO NOT MODIFY BELOW THIS LINE
# The agent reads only the PARAMETERS and BOUNDS dicts above.
