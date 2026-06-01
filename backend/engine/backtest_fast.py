"""Fast universe backtest (A5e) + ablation toggles.

precompute features once per symbol (vectorized), then an O(n) FLAT/LONG loop.
Entry filters are individually toggleable so we can measure each variable's
marginal effect on the edge (the ablation study), rather than force thresholds:

  * regime  — only enter when the market index is above a rising 150-DMA;
  * 52w     — only enter within max_pct_52w of the 52-week high (leaders/new highs);
  * rs      — only enter when the stock's 6mo return beats the index by rs_min.

Exit: "target" (fixed R) or "chandelier" (ride winners, trailing stop).
"""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from typing import Optional

from backend.engine.backtest import BacktestResult, RawTrade, replay_trades
from backend.engine.base import analyze_base
from backend.engine.costs import CostModel
from backend.engine.fills import DEFAULT_SLIPPAGE, fill_entry, fill_stop, resolve_open_bar
from backend.engine.kite_data import Bar
from backend.engine.precompute import precompute_features
from backend.engine.regime import load_regime

TRADEABLE = ("S1B", "S2")
WARMUP = 171
BASE_TAIL = 100


def _chandelier_stop(prev_stop: Decimal, highest_high: Decimal, atr: Decimal, mult: Decimal) -> Decimal:
    return max(prev_stop, highest_high - mult * atr)


def load_bars(con: sqlite3.Connection, symbol: str) -> list[Bar]:
    rows = con.execute(
        "select date,open,high,low,close,volume,delivery_pct from bars "
        "where symbol=? order by date", (symbol,)
    ).fetchall()
    return [
        Bar(date.fromisoformat(d), Decimal(o), Decimal(h), Decimal(l), Decimal(c), int(v), dp)
        for (d, o, h, l, c, v, dp) in rows
    ]


def _fast_simulate(
    symbol, bars, df, *, exit_mode, target_r, chandelier_mult, slippage, min_trp,
    start_date=None, use_regime=False, regime_map=None, use_52w=False, max_pct_52w=15.0,
    use_rs=False, ret_map=None, rs_min=0.0,
) -> list[RawTrade]:
    stages = df["stage"].to_numpy()
    contr = df["is_contraction"].to_numpy()
    avgtrp = df["avg_trp"].to_numpy()
    trig = df["trigger_level"].to_numpy()
    atr = df["atr"].to_numpy()
    pct52 = df["pct_from_52w_high"].to_numpy()
    ret126 = df["ret_126"].to_numpy()
    cm_mult = Decimal(str(chandelier_mult))

    trades: list[RawTrade] = []
    long = False
    entry = stop = target = stopdist = hh = Decimal(0)
    entry_date = None

    for i in range(WARMUP, len(bars)):
        b = bars[i]
        if long:
            if exit_mode == "chandelier":
                if b.low <= stop:
                    fp = fill_stop(stop, b.open, b.low, slippage)
                    trades.append(RawTrade(symbol, entry_date, b.date, entry, fp, stopdist))
                    long = False
                else:
                    if b.high > hh:
                        hh = b.high
                    a = atr[i]
                    if a == a:
                        stop = _chandelier_stop(stop, hh, Decimal(str(round(float(a), 4))), cm_mult)
            else:
                f = resolve_open_bar(b.open, b.high, b.low, stop, target, slippage)
                if f is not None:
                    trades.append(RawTrade(symbol, entry_date, b.date, entry, f.price, stopdist))
                    long = False
            continue

        if start_date is not None and b.date < start_date:
            continue
        j = i - 1
        if not (stages[j] in TRADEABLE and bool(contr[j]) and avgtrp[j] >= min_trp):
            continue
        dj = bars[j].date
        if use_regime and not (regime_map or {}).get(dj, False):
            continue
        if use_52w:
            p = pct52[j]
            if not (p == p) or p > max_pct_52w:
                continue
        if use_rs:
            ir = (ret_map or {}).get(dj)
            sr = ret126[j]
            if ir is None or not (sr == sr) or (sr - ir) < rs_min:
                continue
        if not analyze_base(bars[max(0, j - BASE_TAIL + 1): j + 1]).is_valid_base:
            continue
        trigger = Decimal(str(round(float(trig[j]), 2)))
        sd = trigger * Decimal(str(round(float(avgtrp[j]), 4))) / Decimal(100)
        if sd > 0:
            ent = fill_entry(trigger, b.open, b.high, slippage)
            if ent is not None:
                entry, stopdist = ent, sd
                stop = ent - sd
                target = ent + Decimal(str(target_r)) * sd
                hh = b.high
                entry_date = b.date
                long = True
    return trades


def run_universe_backtest(
    cache_path: str,
    *,
    exit_mode: str = "chandelier",
    starting_capital: Decimal = Decimal("1000000"),
    rpt_pct: float = 0.5,
    target_r: float = 2.0,
    chandelier_mult: float = 3.0,
    slippage: Decimal = DEFAULT_SLIPPAGE,
    cost_model: Optional[CostModel] = None,
    min_trp: float = 2.0,
    min_bars: int = 200,
    max_symbols: Optional[int] = None,
    start_date: Optional[date] = None,
    use_regime: bool = False,
    regime_index: str = "NIFTY 500",
    use_52w: bool = False,
    max_pct_52w: float = 15.0,
    use_rs: bool = False,
    rs_min: float = 0.0,
) -> tuple[BacktestResult, int]:
    regime_map, ret_map = ({}, {})
    if use_regime or use_rs:
        regime_map, ret_map = load_regime(cache_path, regime_index)

    con = sqlite3.connect(cache_path)
    symbols = [r[0] for r in con.execute("select symbol from done order by symbol")]
    if max_symbols:
        symbols = symbols[:max_symbols]

    raw: list[RawTrade] = []
    used = 0
    for s in symbols:
        bars = load_bars(con, s)
        if len(bars) < min_bars:
            continue
        df = precompute_features(bars)
        raw += _fast_simulate(
            s, bars, df, exit_mode=exit_mode, target_r=target_r, chandelier_mult=chandelier_mult,
            slippage=slippage, min_trp=min_trp, start_date=start_date,
            use_regime=use_regime, regime_map=regime_map, use_52w=use_52w, max_pct_52w=max_pct_52w,
            use_rs=use_rs, ret_map=ret_map, rs_min=rs_min,
        )
        used += 1
    con.close()

    res = replay_trades(raw, starting_capital=starting_capital, rpt_pct=rpt_pct, cost_model=cost_model)
    return res, used
