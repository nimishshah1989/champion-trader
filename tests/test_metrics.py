"""Golden tests for per-stock-relative candle features (A3a)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.engine.kite_data import Bar
from backend.engine.metrics import compute_latest_features


def mkbar(i, o, h, l, c, v) -> Bar:
    return Bar(
        date(2026, 1, 1) + timedelta(days=i),
        Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)), v,
    )


def test_ratios_with_identical_prior():
    # 20 flat prior bars (TRP=2, vol=1000), then an expansion bar.
    prior = [mkbar(i, 100, 101, 99, 100, 1000) for i in range(20)]
    latest = mkbar(20, 100, 106, 99, 105, 2000)   # TRP=7/105*100=6.667
    f = compute_latest_features(prior + [latest], lookback=20)
    assert f.trp_ratio == pytest.approx(3.3333, rel=1e-3)
    assert f.close_position == pytest.approx(6 / 7, rel=1e-3)
    assert f.volume_ratio == 2.0
    assert f.is_green is True
    assert f.trp_z == 0.0 and f.volume_z == 0.0   # zero-variance prior


def test_zscores_small_series():
    # prior TRPs [2,4,6] -> mean 4, pstdev sqrt(8/3); latest TRP 8 -> z=2.449
    # prior vols [100,200,300] -> mean 200; latest 400 -> z=2.449
    prior = [
        mkbar(0, 100, 101, 99, 100, 100),
        mkbar(1, 100, 102, 98, 100, 200),
        mkbar(2, 100, 103, 97, 100, 300),
    ]
    latest = mkbar(3, 100, 104, 96, 100, 400)
    f = compute_latest_features(prior + [latest], lookback=3)
    assert f.trp == pytest.approx(8.0)
    assert f.avg_trp == pytest.approx(4.0)
    assert f.trp_ratio == pytest.approx(2.0)
    assert f.trp_z == pytest.approx(2.4495, rel=1e-3)
    assert f.volume_ratio == pytest.approx(2.0)
    assert f.volume_z == pytest.approx(2.4495, rel=1e-3)


def test_requires_enough_bars():
    bars = [mkbar(i, 100, 101, 99, 100, 1000) for i in range(5)]
    with pytest.raises(ValueError):
        compute_latest_features(bars, lookback=20)
