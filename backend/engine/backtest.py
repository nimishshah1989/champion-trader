"""Event-driven backtest loop (A5b) + shared trade replay.

Per symbol: a FLAT/LONG state machine that enters on a READY trigger-break (via
the A4 fill engine) and exits on stop/target with pessimistic intrabar
resolution. `replay_trades` then sizes + costs the raw trades into net-of-cost
R-multiples + an equity curve, scored with the A5a metrics. Shared by the slow
(`run_backtest`, injectable signal) and fast (backtest_fast) paths.

v1 simplifications: trades replayed sequentially (concurrency=R-4); exit = stop
+ fixed R target (ride-winners/trailing=R-3).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Optional

from backend.engine.costs import CostModel
from backend.engine.fills import DEFAULT_SLIPPAGE, fill_entry, resolve_open_bar
from backend.engine.kite_data import Bar
from backend.engine.performance import (
    average_reward_risk,
    calmar,
    expectancy,
    max_drawdown,
    sqn,
    win_rate,
)

SignalFn = Callable[[list[Bar]], Optional[tuple[Decimal, Decimal]]]


@dataclass(frozen=True)
class RawTrade:
    symbol: str
    entry_date: date
    exit_date: date
    entry: Decimal
    exit: Decimal
    stopdist: Decimal


@dataclass(frozen=True)
class BacktestResult:
    r_multiples: list[float]
    equity_curve: list[float]
    sqn: float
    expectancy: float
    win_rate: float
    arr: float
    max_drawdown: float
    calmar: float
    num_trades: int
    final_equity: float


def _simulate_symbol(
    symbol: str, bars: list[Bar], signal_fn: SignalFn, target_r: float, slippage: Decimal, warmup: int
) -> list[RawTrade]:
    trades: list[RawTrade] = []
    long = False
    entry = stop = target = stopdist = Decimal(0)
    entry_date: Optional[date] = None

    for i in range(warmup, len(bars)):
        b = bars[i]
        if long:
            f = resolve_open_bar(b.open, b.high, b.low, stop, target, slippage)
            if f is not None:
                assert entry_date is not None
                trades.append(RawTrade(symbol, entry_date, b.date, entry, f.price, stopdist))
                long = False
        else:
            setup = signal_fn(bars[:i])
            if setup is not None:
                trig, sd = setup
                if sd > 0:
                    ent = fill_entry(trig, b.open, b.high, slippage)
                    if ent is not None:
                        entry, stopdist = ent, sd
                        stop = ent - sd
                        target = ent + Decimal(str(target_r)) * sd
                        entry_date = b.date
                        long = True
    return trades


def replay_trades(
    raw: list[RawTrade],
    *,
    starting_capital: Decimal = Decimal("1000000"),
    rpt_pct: float = 0.5,
    cost_model: Optional[CostModel] = None,
) -> BacktestResult:
    """Size each trade by current equity, apply real costs, build the equity curve."""
    cm = cost_model or CostModel()
    ordered = sorted(raw, key=lambda t: t.exit_date)
    equity = starting_capital
    curve: list[float] = [float(equity)]
    rs: list[float] = []
    rpt = Decimal(str(rpt_pct))

    for t in ordered:
        shares = int((equity * rpt / Decimal(100)) / t.stopdist)
        if shares <= 0:
            continue
        sh = Decimal(shares)
        gross = sh * (t.exit - t.entry)
        costs = cm.buy_costs(sh * t.entry) + cm.sell_costs(sh * t.exit)
        net = gross - costs
        equity = equity + net
        rs.append(float(net / (sh * t.stopdist)))
        curve.append(float(equity))

    return BacktestResult(
        r_multiples=rs,
        equity_curve=curve,
        sqn=sqn(rs),
        expectancy=expectancy(rs),
        win_rate=win_rate(rs),
        arr=average_reward_risk(rs),
        max_drawdown=max_drawdown(curve),
        calmar=calmar(curve),
        num_trades=len(rs),
        final_equity=float(equity),
    )


def run_backtest(
    data: dict[str, list[Bar]],
    signal_fn: SignalFn,
    *,
    starting_capital: Decimal = Decimal("1000000"),
    rpt_pct: float = 0.5,
    target_r: float = 2.0,
    slippage: Decimal = DEFAULT_SLIPPAGE,
    cost_model: Optional[CostModel] = None,
    warmup: int = 1,
) -> BacktestResult:
    raw: list[RawTrade] = []
    for sym, bars in data.items():
        raw += _simulate_symbol(sym, bars, signal_fn, target_r, slippage, warmup)
    return replay_trades(raw, starting_capital=starting_capital, rpt_pct=rpt_pct, cost_model=cost_model)
