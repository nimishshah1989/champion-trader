"""Fast universe backtest (A5e) with selectable exit policy.

precompute features once per symbol (vectorized), then an O(n) FLAT/LONG loop on
precomputed arrays. analyze_base is called only on the rare candidate bars
(stage & contraction & TRP pass), on a ~100-bar tail (constant work).

Exit policies:
  * "target"     — stop + fixed R target (v1; caps the right tail).
  * "chandelier" — ride winners: stop + a trailing stop = highest-high-since-entry
                   - mult*ATR, ratcheting UP only, no fixed target. Captures the
                   fat-tail runners this style lives on. (R-3 lever.)
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

TRADEABLE = ("S1B", "S2")
WARMUP = 171
BASE_TAIL = 100


def _chandelier_stop(prev_stop: Decimal, highest_high: Decimal, atr: Decimal, mult: Decimal) -> Decimal:
    """Trailing stop = HH - mult*ATR, but never below the prior stop (ratchets up)."""
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
    symbol, bars, df, *, exit_mode, target_r, chandelier_mult, slippage, min_trp
) -> list[RawTrade]:
    stages = df["stage"].to_numpy()
    contr = df["is_contraction"].to_numpy()
    avgtrp = df["avg_trp"].to_numpy()
    trig = df["trigger_level"].to_numpy()
    atr = df["atr"].to_numpy()
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
                    if a == a:  # not NaN
                        stop = _chandelier_stop(stop, hh, Decimal(str(round(float(a), 4))), cm_mult)
            else:
                f = resolve_open_bar(b.open, b.high, b.low, stop, target, slippage)
                if f is not None:
                    trades.append(RawTrade(symbol, entry_date, b.date, entry, f.price, stopdist))
                    long = False
        else:
            j = i - 1
            if stages[j] in TRADEABLE and bool(contr[j]) and avgtrp[j] >= min_trp:
                if analyze_base(bars[max(0, j - BASE_TAIL + 1): j + 1]).is_valid_base:
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
) -> tuple[BacktestResult, int]:
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
            s, bars, df, exit_mode=exit_mode, target_r=target_r,
            chandelier_mult=chandelier_mult, slippage=slippage, min_trp=min_trp,
        )
        used += 1
    con.close()

    res = replay_trades(raw, starting_capital=starting_capital, rpt_pct=rpt_pct, cost_model=cost_model)
    return res, used
