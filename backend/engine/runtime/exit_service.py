"""v2 exit engine — close-based stop + 5xATR chandelier trail (extracted runtime).

This per-bar exit decision until now existed only inline inside
`backtest_fast._fast_simulate` (exit_mode="chandelier"). Extracting it here lets
the LIVE app and the backtest share one implementation — the source of the edge.

Rules (matching the validated v2 exactly):
  * close-based stop: exit if the bar CLOSES below the stop, or GAPS below it at the
    open; an intraday wick through the stop does NOT exit (Afzal reviews at EOD).
  * trail: stop = max(prev_stop, highest_high - mult*ATR), ratchets UP only.
  * fills: gap-down fills at the open, close-break fills at the close (pessimistic,
    via fills.fill_stop) — byte-identical to the backtest.

Call `init_trail` once at entry, then `step` once per subsequent bar.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from backend.engine.fills import DEFAULT_SLIPPAGE, fill_stop
from backend.engine.kite_data import Bar
from backend.engine.runtime.config import STRATEGY_V2, StrategyParams


def chandelier_stop(prev_stop: Decimal, highest_high: Decimal, atr: Decimal, mult: Decimal) -> Decimal:
    """The ratchet: never lower the stop; raise it to highest_high - mult*ATR."""
    return max(prev_stop, highest_high - mult * atr)


@dataclass
class TrailState:
    entry: Decimal
    stopdist: Decimal        # initial 1R distance (entry - stop at entry)
    stop: Decimal            # current (ratcheting) stop level
    highest_high: Decimal    # running peak since entry
    mult: Decimal = STRATEGY_V2.chandelier_mult


@dataclass
class ExitDecision:
    exited: bool
    fill_price: Optional[Decimal] = None
    reason: Optional[str] = None     # "GAP" | "CLOSE"


def init_trail(entry: Decimal, stopdist: Decimal, breakout_high: Decimal,
               params: StrategyParams = STRATEGY_V2) -> TrailState:
    """Open the trail at entry: stop = entry - 1R, peak = the breakout bar's high."""
    return TrailState(entry=entry, stopdist=stopdist, stop=entry - stopdist,
                      highest_high=breakout_high, mult=params.chandelier_mult)


def step(trail: TrailState, bar: Bar, atr: Optional[float],
         slippage: Decimal = DEFAULT_SLIPPAGE) -> ExitDecision:
    """Advance the trail by one bar. Mutates `trail` (highest_high, stop).

    `atr` is the current bar's ATR (float, may be NaN before warmup). Returns an
    ExitDecision; if `exited`, the caller closes the position at `fill_price`.
    """
    gapped = bar.open <= trail.stop      # overnight gap through the stop
    closed = bar.close < trail.stop      # EOD close below the stop
    if gapped or closed:
        fill_px = bar.open if gapped else bar.close
        fp = fill_stop(trail.stop, fill_px, fill_px, slippage)
        return ExitDecision(exited=True, fill_price=fp, reason="GAP" if gapped else "CLOSE")
    if bar.high > trail.highest_high:
        trail.highest_high = bar.high
    if atr is not None and atr == atr:   # skip NaN (pre-warmup ATR)
        trail.stop = chandelier_stop(trail.stop, trail.highest_high,
                                     Decimal(str(round(float(atr), 4))), trail.mult)
    return ExitDecision(exited=False)
