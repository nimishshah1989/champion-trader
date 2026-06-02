"""PPC/NPC detection + watchlist-state assembly (A3e).

Ties the signal modules together. Headline fix: READY now means
"contraction + trigger identified" (a coiling stock ready to break), NOT the
legacy "Stage 2 + N base-days". Stage, relative strength, and sector strength
are hard gates. Output carries an explainable `reasons` trail.

    candle  = the trigger  (PPC range/volume/close expansion)
    context = the edge     (stage + base + contraction + RS + sector)

RS/sector data wiring is A3f; here they are optional inputs (None = not yet
evaluated, non-blocking) so the price-based logic can be built and tested now.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from backend.engine.base import analyze_base
from backend.engine.contraction import detect_contraction
from backend.engine.kite_data import Bar
from backend.engine.metrics import CandleFeatures
from backend.engine.stage import classify_stage

READY, NEAR, AWAY = "READY", "NEAR", "AWAY"
TRADEABLE_STAGES = ("S1B", "S2")


@dataclass(frozen=True)
class SignalParams:
    ppc_trp_ratio_min: float = 1.5
    ppc_close_pos_min: float = 0.60
    ppc_volume_ratio_min: float = 1.5
    npc_trp_ratio_min: float = 1.5
    npc_close_pos_max: float = 0.40
    npc_volume_ratio_min: float = 1.5
    rs_min_percentile: float = 70.0


@dataclass(frozen=True)
class WatchState:
    bucket: str
    stage: str
    stage_ok: bool
    base_ok: bool
    contraction_ok: bool
    rs_ok: bool
    sector_ok: bool
    trigger_level: Decimal
    reasons: tuple[str, ...]


def detect_ppc_candle(f: CandleFeatures, params: SignalParams = SignalParams()) -> bool:
    return (
        f.trp_ratio >= params.ppc_trp_ratio_min
        and f.close_position >= params.ppc_close_pos_min
        and f.volume_ratio >= params.ppc_volume_ratio_min
        and f.is_green
    )


def detect_npc_candle(f: CandleFeatures, params: SignalParams = SignalParams()) -> bool:
    return (
        f.trp_ratio >= params.npc_trp_ratio_min
        and f.close_position <= params.npc_close_pos_max
        and f.volume_ratio >= params.npc_volume_ratio_min
        and not f.is_green
    )


def _bucket(stage_ok: bool, base_ok: bool, contraction_ok: bool, rs_ok: bool, sector_ok: bool) -> str:
    if not (stage_ok and rs_ok and sector_ok):
        return AWAY
    if base_ok and contraction_ok:
        return READY          # contraction + trigger identified
    if base_ok:
        return NEAR           # basing, not yet coiling/triggered
    return AWAY


def classify_watch_state(
    bars: list[Bar],
    params: SignalParams = SignalParams(),
    *,
    rs_percentile: Optional[float] = None,
    sector_strong: Optional[bool] = None,
) -> WatchState:
    stage = classify_stage(bars)
    stage_ok = stage in TRADEABLE_STAGES
    base = analyze_base(bars)
    contraction = detect_contraction(bars)
    rs_ok = (rs_percentile is None) or (rs_percentile >= params.rs_min_percentile)
    sector_ok = True if sector_strong is None else bool(sector_strong)

    bucket = _bucket(stage_ok, base.is_valid_base, contraction.is_contraction, rs_ok, sector_ok)
    trigger = contraction.trigger_level if contraction.is_contraction else base.pivot_high
    reasons = (
        f"stage={stage}{'' if stage_ok else ' (avoid)'}",
        f"base={'valid' if base.is_valid_base else 'no'} ({base.base_bars}d/{base.depth_pct:.0f}%)",
        f"contraction={'yes' if contraction.is_contraction else 'no'}",
        f"RS={'ok' if rs_ok else 'weak'}",
        f"sector={'strong' if sector_ok else 'weak'}",
    )
    return WatchState(
        bucket, stage, stage_ok, base.is_valid_base, contraction.is_contraction,
        rs_ok, sector_ok, trigger, reasons,
    )
