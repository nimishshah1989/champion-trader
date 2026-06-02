"""Production signal_fn (A5c): wraps the A3 detectors into the backtest contract.

    signal_fn(history) -> (trigger, stop_distance) | None

  * needs >= MIN_BARS of history (the stage filter needs ~170 bars);
  * enforces the min-TRP tradeability gate (>= 2.0) the legacy scanner skipped;
  * fires only when classify_watch_state == READY (contraction + trigger);
  * stop distance = trigger * avg_TRP%  (the methodology's TRP-based stop).

RS/sector gates default to non-blocking until A3f wires index data.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, Optional

from backend.engine.kite_data import Bar
from backend.engine.metrics import compute_latest_features
from backend.engine.signals import READY, SignalParams, classify_watch_state

MIN_BARS = 171
MIN_TRP = 2.0


def production_signal(
    params: SignalParams = SignalParams(), min_trp: float = MIN_TRP
) -> Callable[[list[Bar]], Optional[tuple[Decimal, Decimal]]]:
    def fn(history: list[Bar]) -> Optional[tuple[Decimal, Decimal]]:
        if len(history) < MIN_BARS:
            return None
        feats = compute_latest_features(history)
        if feats.avg_trp < min_trp:                     # tradeability gate (council fix)
            return None
        ws = classify_watch_state(history, params)
        if ws.bucket != READY:
            return None
        trigger = ws.trigger_level
        stopdist = trigger * Decimal(str(feats.avg_trp)) / Decimal(100)
        return (trigger, stopdist) if stopdist > 0 else None

    return fn
