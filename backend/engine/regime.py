"""Market-regime + relative-strength context from the cached NIFTY index.

regime_on[date]  = index close above a RISING 150-DMA (only buy breakouts in a
                   confirmed market uptrend).
index_ret126[d]  = the index's 126-day (~6mo) return, for RS = stock_ret - index_ret.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

import pandas as pd


def load_regime(
    cache_path: str, index_code: str = "NIFTY 500", sma_window: int = 150, slope_lb: int = 20
) -> tuple[dict[date, bool], dict[date, Optional[float]]]:
    con = sqlite3.connect(cache_path)
    rows = con.execute(
        "select date, close from index_bars where index_code=? order by date", (index_code,)
    ).fetchall()
    con.close()

    regime_on: dict[date, bool] = {}
    index_ret126: dict[date, Optional[float]] = {}
    if not rows:
        return regime_on, index_ret126

    df = pd.DataFrame(rows, columns=["date", "close"])
    dts = [date.fromisoformat(d) for d in df["date"]]
    c = df["close"].astype(float)
    sma = c.rolling(sma_window).mean()
    on = (c > sma) & (sma > sma.shift(slope_lb))
    ret = c / c.shift(126) - 1
    for d, o, r in zip(dts, on.fillna(False), ret):
        regime_on[d] = bool(o)
        index_ret126[d] = float(r) if r == r else None   # NaN -> None
    return regime_on, index_ret126
