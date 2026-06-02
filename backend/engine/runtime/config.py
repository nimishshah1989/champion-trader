"""Typed, frozen, versioned strategy + risk configuration — the single source of tunables.

Per ARCHITECTURE.md rule #3: every threshold the validated v2 strategy depends on lives
HERE, never as a literal sprinkled through the code. Configs are **named & versioned** so
a change is a deliberate, auditable, roll-back-able act (clone -> A/B walk-forward ->
adopt only on a plateau), and every trade persists which ``version`` produced it.

The defaults below ARE the validated v2 (parity-proven against ``backtest_fast``, 293/293):
  * StrategyParams — per-symbol signal logic, consumed by ``signal_service`` (entry) and
    ``exit_service`` (exit).
  * RiskParams     — the portfolio overlay, consumed by ``risk_manager``.

Frozen dataclasses: a config is immutable once built. To sophisticate safely, build a new
named instance (``dataclasses.replace(STRATEGY_V2, vol_breakout_k=3.0, version="v2.1")``),
A/B it, and only then flip the live default.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StrategyParams:
    """Per-symbol signal logic (entry gates + exit trail). The validated v2 thresholds.

    These are pre-registered (O'Neil/Weinstein-grounded), NOT data-mined per regime or cap.
    """

    version: str = "v2"
    # --- entry gates (all must hold on the signal bar) ---
    min_trp: float = 2.0                          # min avg daily TRP% to be tradeable
    vol_breakout_k: float = 2.0                   # breakout-bar volume >= k x 50d-avg (0 disables the v2 gate)
    skip_circuit_locked: bool = True              # don't chase an unfillable upper-band lock
    # --- exit trail ---
    chandelier_mult: Decimal = Decimal("5.0")     # trailing stop = highest_high - mult x ATR (ratchets up only)


@dataclass(frozen=True)
class SlippageTier:
    """One band of the tiered execution-slippage model (liquid names slip less)."""

    min_turnover_cr: float       # applies to names with daily turnover >= this (Rs cr)
    bps: Decimal                 # one-side slippage as a fraction (e.g. 0.0010 = 10 bps)


@dataclass(frozen=True)
class RiskParams:
    """Portfolio overlay: sizing, position caps, regime bear-sizing, drawdown breaker.

    Consumed by ``risk_manager``. The ``slippage_tiers`` (10/25/50/100 bps by turnover)
    were duplicated as a local ``slip()`` in every research script — they live here now.
    """

    version: str = "v2"
    rpt_pct: float = 0.35                         # risk per trade, % of equity
    max_positions: int = 15                       # max concurrent positions
    bear_frac: Decimal = Decimal("0.25")          # size multiple when market < rising N-DMA
    dd_halt: float = 0.15                          # halt new entries at -15% from the equity peak
    dd_resume: float = 0.075                       # resume when back within -7.5% of the peak
    idle_yield: float = 0.065                      # annual yield on idle cash (Liquid Bees)
    liquidity_floor_cr: float = 5.0                # only trade names >= Rs X cr/day turnover (paper default; 15 for large capital)
    regime_sma_window: int = 50                    # bear flag: NIFTY 500 vs its rising N-DMA (NOT the 150-DMA entry default)
    regime_slope_lb: int = 5                       # ... rising = SMA today > SMA slope_lb sessions ago
    # tiered one-side execution slippage — highest turnover floor FIRST (matched top-down)
    slippage_tiers: tuple[SlippageTier, ...] = (
        SlippageTier(15.0, Decimal("0.0010")),     # >= Rs15cr/day -> 10 bps
        SlippageTier(5.0, Decimal("0.0025")),      # >= Rs 5cr/day -> 25 bps
        SlippageTier(1.0, Decimal("0.0050")),      # >= Rs 1cr/day -> 50 bps
        SlippageTier(0.0, Decimal("0.0100")),      # the rest      -> 100 bps
    )

    def slippage_for(self, turnover_cr: float) -> Decimal:
        """One-side slippage for a name of the given daily turnover (Rs cr)."""
        for tier in self.slippage_tiers:
            if turnover_cr >= tier.min_turnover_cr:
                return tier.bps
        return self.slippage_tiers[-1].bps


# --- the named, validated default config family ---------------------------------------
STRATEGY_V2 = StrategyParams()    # the parity-proven entry/exit thresholds
RISK_V2 = RiskParams()            # the validated portfolio overlay (RPT 0.35, max 15, ...)
