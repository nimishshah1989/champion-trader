"""v2 entry signal — extracted runtime (upgrades production_signal from v1 to v2).

Mirrors the entry gate inside `backtest_fast._fast_simulate` for the validated v2:

    stage in (S1B, S2)  AND  contraction  AND  avg_trp >= min_trp  AND  valid base
    AND breakout-day volume >= vol_breakout_k * 50d-avg  AND  not circuit-locked,
    then fill the break of the 5-day-high trigger (pessimistic gap-up fill).

The thresholds come from a typed, versioned `StrategyParams` (config.py) — never literals
here — so a change is deliberate, auditable, and re-validated; never auto-tuned.

Two entry points:
  * entry_at(ctx, i, ...)        — array-driven (engine/backtest + parity harness)
  * evaluate_entry(history, ...) — live-callable: pass a list[Bar], get a signal | None
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import numpy as np

from backend.engine.base import analyze_base
from backend.engine.fills import DEFAULT_SLIPPAGE, fill_entry
from backend.engine.kite_data import Bar
from backend.engine.precompute import precompute_features
from backend.engine.runtime.config import STRATEGY_V2, StrategyParams

TRADEABLE = ("S1B", "S2")
WARMUP = 171          # matches backtest_fast.WARMUP (stage filter needs ~170 bars)
BASE_TAIL = 100       # matches backtest_fast.BASE_TAIL (base analysed on last 100 bars)


@dataclass
class EntryContext:
    """Precomputed feature arrays for one symbol (aligned to `bars` by index)."""
    bars: list[Bar]
    stages: np.ndarray
    contr: np.ndarray
    avgtrp: np.ndarray
    trig: np.ndarray
    vol_sma50: np.ndarray


@dataclass
class Setup:
    """A v2 SETUP on the signal bar (pre-breakout): the watchlist candidate for tomorrow."""
    trigger: Decimal        # break level for tomorrow = 5-day high on the signal bar
    stopdist: Decimal       # 1R distance = trigger * avg_trp%
    avg_trp: float
    stage: str              # S1B / S2


@dataclass
class EntrySignal:
    entry: Decimal          # filled entry price (after slippage)
    trigger: Decimal        # break level (5-day high)
    stopdist: Decimal       # 1R distance = trigger * avg_trp%
    avg_trp: float
    volume_ratio: float     # breakout-bar volume / 50d-avg


def _circuit_locked(prev_close: Decimal, bar: Bar) -> bool:
    """Unfillable upper-band lock: fully frozen bar, or >=19.5% surge closing on its high."""
    if prev_close <= 0:
        return False
    gain = (bar.close - prev_close) / prev_close
    return bar.high == bar.low or (gain >= Decimal("0.195") and (bar.high - bar.close) <= bar.close * Decimal("0.003"))


def setup_at(ctx: EntryContext, j: int, *, params: StrategyParams = STRATEGY_V2) -> Optional[Setup]:
    """Is signal bar `j` a v2 SETUP? Stage S1B/S2 + contraction + valid base + avgTRP>=min.

    This is the per-stock strength gate WITHOUT the breakout/volume/circuit checks — i.e.
    a watchlist candidate carrying tomorrow's trigger (the 5-day high) and its 1R stop. The
    breakout + >=2x volume + circuit-skip are applied later (`entry_at` on bar j+1, or live).
    """
    if j < WARMUP - 1:
        return None
    if not (ctx.stages[j] in TRADEABLE and bool(ctx.contr[j]) and ctx.avgtrp[j] >= params.min_trp):
        return None
    if not analyze_base(ctx.bars[max(0, j - BASE_TAIL + 1): j + 1]).is_valid_base:
        return None
    trigger = Decimal(str(round(float(ctx.trig[j]), 2)))   # same rounding as the engine
    avg_trp = round(float(ctx.avgtrp[j]), 4)
    sd = trigger * Decimal(str(avg_trp)) / Decimal(100)
    if sd <= 0:
        return None
    return Setup(trigger=trigger, stopdist=sd, avg_trp=avg_trp, stage=str(ctx.stages[j]))


def entry_at(ctx: EntryContext, i: int, *, params: StrategyParams = STRATEGY_V2,
             slippage: Decimal = DEFAULT_SLIPPAGE) -> Optional[EntrySignal]:
    """Is bar `i` a v2 entry? = SETUP on j=i-1, then breakout/volume/circuit/fill on bar i."""
    if i < WARMUP:
        return None
    j = i - 1
    setup = setup_at(ctx, j, params=params)
    if setup is None:
        return None
    bars = ctx.bars
    b = bars[i]
    # breakout-bar volume confirmation (the v2 gate)
    vol_ratio = float("nan")
    v50 = ctx.vol_sma50[i]
    if v50 == v50 and v50 > 0:
        vol_ratio = bars[i].volume / v50
    if params.vol_breakout_k > 0:
        if not (v50 == v50) or v50 <= 0 or bars[i].volume < params.vol_breakout_k * v50:
            return None
    if params.skip_circuit_locked and _circuit_locked(bars[j].close, b):
        return None
    ent = fill_entry(setup.trigger, b.open, b.high, slippage)
    if ent is None:                       # bar's high never reached the trigger
        return None
    return EntrySignal(entry=ent, trigger=setup.trigger, stopdist=setup.stopdist,
                       avg_trp=setup.avg_trp, volume_ratio=vol_ratio)


def context_from_df(bars: list[Bar], df) -> EntryContext:
    return EntryContext(
        bars=bars,
        stages=df["stage"].to_numpy(),
        contr=df["is_contraction"].to_numpy(),
        avgtrp=df["avg_trp"].to_numpy(),
        trig=df["trigger_level"].to_numpy(),
        vol_sma50=df["vol_sma50"].to_numpy(),
    )


def evaluate_entry(history: list[Bar], *, params: StrategyParams = STRATEGY_V2,
                   slippage: Decimal = DEFAULT_SLIPPAGE) -> Optional[EntrySignal]:
    """Live API: given a symbol's recent bars (newest last), is TODAY a v2 entry (breakout)?"""
    if len(history) <= WARMUP:
        return None
    df = precompute_features(history)
    ctx = context_from_df(history, df)
    return entry_at(ctx, len(history) - 1, params=params, slippage=slippage)


def detect_setup(history: list[Bar], *, params: StrategyParams = STRATEGY_V2) -> Optional[Setup]:
    """Live API (watchlist): is the latest bar a v2 SETUP ready to trigger tomorrow?"""
    if len(history) < WARMUP:
        return None
    df = precompute_features(history)
    ctx = context_from_df(history, df)
    return setup_at(ctx, len(history) - 1, params=params)
