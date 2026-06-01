"""Performance metrics (A5a) — the objective (SQN) + diagnostics.

Per the locked objective: maximize SQN (risk- and sample-adjusted mean R), with
expectancy / win-rate / ARR / Calmar / max-drawdown as reported diagnostics.
Pure functions over a list of trade R-multiples and/or an equity curve.
"""
from __future__ import annotations

from math import sqrt
from statistics import fmean, pstdev

SQN_N_CAP = 100   # Van Tharp caps the sample-size term at 100


def expectancy(r_multiples: list[float]) -> float:
    return fmean(r_multiples) if r_multiples else 0.0


def win_rate(r_multiples: list[float]) -> float:
    if not r_multiples:
        return 0.0
    return sum(1 for r in r_multiples if r > 0) / len(r_multiples)


def average_reward_risk(r_multiples: list[float]) -> float:
    """Avg winning R / avg losing R (ARR). inf if no losses, 0 if no wins."""
    wins = [r for r in r_multiples if r > 0]
    losses = [-r for r in r_multiples if r < 0]
    if not wins:
        return 0.0
    if not losses:
        return float("inf")
    return fmean(wins) / fmean(losses)


def sqn(r_multiples: list[float]) -> float:
    """System Quality Number = mean(R)/std(R) * sqrt(min(N, 100))."""
    n = len(r_multiples)
    if n < 2:
        return 0.0
    sd = pstdev(r_multiples)
    if sd == 0:
        return 0.0
    return fmean(r_multiples) / sd * sqrt(min(n, SQN_N_CAP))


def max_drawdown(equity_curve: list[float]) -> float:
    """Max peak-to-trough drawdown as a positive fraction (0..1)."""
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    mdd = 0.0
    for v in equity_curve:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return mdd


def calmar(equity_curve: list[float], trading_days_per_year: int = 252) -> float:
    """Annualized return / max drawdown."""
    if len(equity_curve) < 2 or equity_curve[0] <= 0:
        return 0.0
    mdd = max_drawdown(equity_curve)
    if mdd == 0:
        return 0.0
    total_return = equity_curve[-1] / equity_curve[0] - 1
    years = (len(equity_curve) - 1) / trading_days_per_year
    if years <= 0:
        return 0.0
    growth = 1 + total_return
    annualized = growth ** (1 / years) - 1 if growth > 0 else -1.0
    return annualized / mdd
