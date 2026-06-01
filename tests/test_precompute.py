"""Differential test: the vectorized feature engine (A5d) must match the
pure-Python detectors bar-for-bar (this also re-proves no look-ahead, since
precompute row k must equal the pure-Python result on bars[:k+1])."""
import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.engine.contraction import detect_contraction
from backend.engine.kite_data import Bar
from backend.engine.metrics import compute_latest_features
from backend.engine.precompute import precompute_features
from backend.engine.stage import classify_stage


def _synth(n=260):
    bars, prevc = [], 100.0
    for i in range(n):
        c = 100 + 20 * math.sin(i / 15) + i * 0.05
        o = prevc
        rng = 1.0 + 0.5 * abs(math.sin(i / 7))
        h = max(o, c) + rng
        l = min(o, c) - rng
        vol = 1000 + int(500 * abs(math.sin(i / 5)))
        bars.append(Bar(date(2015, 1, 1) + timedelta(days=i),
                        Decimal(str(round(o, 2))), Decimal(str(round(h, 2))),
                        Decimal(str(round(l, 2))), Decimal(str(round(c, 2))), vol))
        prevc = c
    return bars


BARS = _synth(260)
DF = precompute_features(BARS)


@pytest.mark.parametrize("k", [180, 205, 230, 259])
def test_vectorized_matches_pure_python(k):
    row = DF.iloc[k]
    hist = BARS[: k + 1]

    f = compute_latest_features(hist)
    assert row["trp_ratio"] == pytest.approx(f.trp_ratio, abs=1e-9)
    assert row["trp_z"] == pytest.approx(f.trp_z, abs=1e-9)
    assert row["close_position"] == pytest.approx(f.close_position, abs=1e-9)
    assert row["volume_ratio"] == pytest.approx(f.volume_ratio, abs=1e-9)
    assert row["volume_z"] == pytest.approx(f.volume_z, abs=1e-9)
    assert bool(row["is_green"]) == f.is_green

    assert row["stage"] == classify_stage(hist)

    con = detect_contraction(hist)
    assert row["atr_percentile"] == pytest.approx(con.atr_percentile, abs=1e-9)
    assert row["atr_slope_pct"] == pytest.approx(con.atr_slope_pct, abs=1e-9)
    assert bool(row["is_contraction"]) == con.is_contraction


def test_no_lookahead_truncation_equivalence():
    # precompute on a truncated series must equal the full-series row at that index
    k = 200
    df_trunc = precompute_features(BARS[: k + 1])
    assert df_trunc.iloc[k]["stage"] == DF.iloc[k]["stage"]
    assert df_trunc.iloc[k]["trp_ratio"] == pytest.approx(DF.iloc[k]["trp_ratio"], abs=1e-9)
    assert df_trunc.iloc[k]["atr_percentile"] == pytest.approx(DF.iloc[k]["atr_percentile"], abs=1e-9)
