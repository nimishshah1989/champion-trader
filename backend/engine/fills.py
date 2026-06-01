"""Fill engine (A4) — honest, pessimistic daily-bar fills.

Removes the legacy optimism where stops magically filled at the stop on a
gap-down. Conventions:
  * entry  -> fills at max(trigger, open) + buy slippage   (a gap-up costs you)
  * stop   -> fills at min(stop,  open) - sell slippage     (a gap-DOWN fills below the stop)
  * target -> fills at the target (limit) - sell slippage
  * intrabar ambiguity: if one daily bar touches BOTH stop and target, the STOP
    wins — we cannot see order within a daily bar, so we assume the worse case.
All money is Decimal.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

DEFAULT_SLIPPAGE = Decimal("0.0010")   # 10 bps each side
_P = Decimal("0.01")


def _q(x: Decimal) -> Decimal:
    return x.quantize(_P, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Fill:
    price: Decimal
    reason: str   # ENTRY | STOP | TARGET


def fill_entry(
    trigger: Decimal, day_open: Decimal, day_high: Decimal, slippage: Decimal = DEFAULT_SLIPPAGE
) -> Optional[Decimal]:
    if day_high < trigger:
        return None
    raw = max(trigger, day_open)                 # gap-up: pay the (higher) open
    return _q(raw * (Decimal(1) + slippage))


def fill_stop(
    stop: Decimal, day_open: Decimal, day_low: Decimal, slippage: Decimal = DEFAULT_SLIPPAGE
) -> Optional[Decimal]:
    if day_low > stop:
        return None
    raw = min(stop, day_open)                    # gap-down: get the (lower) open
    return _q(raw * (Decimal(1) - slippage))


def fill_target(
    target: Decimal, day_open: Decimal, day_high: Decimal, slippage: Decimal = DEFAULT_SLIPPAGE
) -> Optional[Decimal]:
    if day_high < target:
        return None
    return _q(target * (Decimal(1) - slippage))   # limit at the target


def resolve_open_bar(
    day_open: Decimal,
    day_high: Decimal,
    day_low: Decimal,
    stop: Decimal,
    target: Optional[Decimal] = None,
    slippage: Decimal = DEFAULT_SLIPPAGE,
) -> Optional[Fill]:
    """Pessimistic intrabar resolution for one open long position on one bar."""
    s = fill_stop(stop, day_open, day_low, slippage)
    if s is not None:
        return Fill(s, "STOP")                   # stop wins ties (pessimistic)
    if target is not None:
        t = fill_target(target, day_open, day_high, slippage)
        if t is not None:
            return Fill(t, "TARGET")
    return None
