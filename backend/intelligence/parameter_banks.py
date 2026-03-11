"""
parameter_banks.py — Regime-specific parameter overrides.

Each regime has a set of parameter adjustments that are applied on top
of the current strategy.py PARAMETERS when that regime is active.

The AutoOptimize loop can evolve these values over time.
Initial values are sensible defaults based on methodology understanding.
"""

import logging
from typing import Optional

from backend.intelligence.strategy import PARAMETERS, BOUNDS

logger = logging.getLogger(__name__)


REGIME_BANKS: dict[str, dict[str, float]] = {
    "TRENDING_BULL": {
        # Looser thresholds — more signals in trends
        "ppc_trp_ratio_min": 1.3,
        "ppc_volume_ratio_min": 1.3,
        "min_base_days": 18,
        "contraction_narrowing_min": 2,
    },
    "RANGING_QUIET": {
        # Tighter thresholds — fewer false signals in choppy markets
        "ppc_trp_ratio_min": 1.7,
        "ppc_close_position_min": 0.65,
        "ppc_volume_ratio_min": 1.7,
        "min_base_days": 25,
    },
    "HIGH_VOLATILITY": {
        # Demand more confirmation
        "ppc_volume_ratio_min": 2.0,
        "npc_volume_ratio_min": 2.0,
        "contraction_resistance_pct": 4.0,
        "min_base_days": 25,
    },
    "WEAKENING_BEAR": {
        # Very selective — demand strong bases, tight signals
        "ppc_trp_ratio_min": 1.8,
        "ppc_close_position_min": 0.70,
        "ppc_volume_ratio_min": 1.8,
        "min_base_days": 30,
        "contraction_narrowing_min": 4,
    },
}

# Track which bank is currently active
_active_regime: Optional[str] = None
_active_version: str = "default_v1"


def get_active_parameters(regime: str) -> dict[str, float]:
    """
    Get the effective parameters for a given regime.
    Starts with base PARAMETERS and overlays regime-specific adjustments.
    All values are validated against BOUNDS.
    """
    global _active_regime, _active_version

    effective = dict(PARAMETERS)

    if regime in REGIME_BANKS:
        overrides = REGIME_BANKS[regime]
        for key, value in overrides.items():
            if key in BOUNDS:
                lo, hi = BOUNDS[key]
                clamped = max(lo, min(hi, value))
                effective[key] = clamped
            else:
                logger.warning(f"Unknown parameter in regime bank: {key}")

    _active_regime = regime
    _active_version = f"{regime.lower()}_v1"

    logger.info(f"Active parameter bank: {_active_version} ({len(REGIME_BANKS.get(regime, {}))} overrides)")
    return effective


def get_active_version() -> str:
    """Get version string of the currently active parameter bank."""
    return _active_version


def get_bank_info() -> dict:
    """Get info about all regime banks."""
    return {
        "active_regime": _active_regime,
        "active_version": _active_version,
        "banks": {
            regime: {
                "overrides": overrides,
                "override_count": len(overrides),
            }
            for regime, overrides in REGIME_BANKS.items()
        },
    }
