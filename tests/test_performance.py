"""Golden tests for performance metrics (A5a)."""
import pytest

from backend.engine.performance import (
    average_reward_risk,
    calmar,
    expectancy,
    max_drawdown,
    sqn,
    win_rate,
)


def test_expectancy():
    assert expectancy([1, 1, 1, -1]) == 0.5
    assert expectancy([]) == 0.0


def test_win_rate():
    assert win_rate([1, 1, 1, -1]) == 0.75
    assert win_rate([]) == 0.0


def test_average_reward_risk():
    assert average_reward_risk([2, 2, -1, -1]) == 2.0
    assert average_reward_risk([2, 2]) == float("inf")     # no losses
    assert average_reward_risk([-1, -1]) == 0.0            # no wins


def test_sqn_zero_variance_or_tiny_sample():
    assert sqn([1, 1, 1, 1]) == 0.0
    assert sqn([1]) == 0.0


def test_sqn_known_value():
    # r=[2,-1]*4: mean 0.5, pstdev 1.5, sqrt(8) -> 0.5/1.5*2.8284 = 0.9428
    assert sqn([2, -1, 2, -1, 2, -1, 2, -1]) == pytest.approx(0.9428, rel=1e-3)


def test_max_drawdown():
    assert max_drawdown([100, 120, 90, 150]) == pytest.approx(0.25)
    assert max_drawdown([100, 110, 121]) == 0.0
    assert max_drawdown([100]) == 0.0


def test_calmar():
    # 100 -> 80 (20% DD) -> 200 over ~1 year: annualized 100% / 20% DD = ~5
    curve = [100, 80] + [80 + 120 * k / 251 for k in range(1, 252)]
    assert calmar(curve, trading_days_per_year=252) == pytest.approx(5.0, rel=0.05)
