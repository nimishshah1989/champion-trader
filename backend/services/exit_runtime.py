"""Post-close v2 exit job — the close-based 5xATR chandelier exit on open trades.

Replaces the legacy intraday-touch 2R/4R/8R/12R ladder. Per the validated strategy (and
the user's decision) it runs in two moments:
  * run_eod_exits        — once after the official close: exit on a close below the trail,
                           else ratchet the trail up and persist it.
  * run_morning_gap_exits — at 09:15: exit any position that GAPS open below its stop.

Each open trade's chandelier trail is reconstructed from its persisted columns
(current_stop / highest_high), self-healing from sl_price / avg_entry_price for trades
created before the trail columns existed. Pure orchestration: a DB session + a market-store
connection in, trade mutations + a summary out — no network, no scheduler, no clock.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from statistics import median
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import Trade
from backend.engine.backtest_fast import load_bars
from backend.engine.precompute import precompute_features
from backend.engine.runtime.config import RISK_V2, STRATEGY_V2, RiskParams, StrategyParams
from backend.engine.runtime.exit_service import TrailState
from backend.services import strategy_runtime as sr

_OPEN = ("OPEN", "PARTIAL")


def _bars_as_of(con: sqlite3.Connection, symbol: str, as_of: Optional[date]) -> list:
    bars = load_bars(con, symbol)
    return [b for b in bars if as_of is None or b.date <= as_of]


def _trail_for(trade: Trade, params: StrategyParams) -> Optional[TrailState]:
    """Rebuild a trade's chandelier trail, self-healing missing columns from entry/SL."""
    if trade.avg_entry_price is None:
        return None
    entry = Decimal(str(trade.avg_entry_price))
    if trade.sl_price is not None:
        stopdist = entry - Decimal(str(trade.sl_price))
    elif trade.trp_at_entry is not None:
        stopdist = Decimal(str(trade.trp_at_entry))
    else:
        return None
    if stopdist <= 0:
        return None
    current_stop = Decimal(str(trade.current_stop)) if trade.current_stop is not None else entry - stopdist
    highest_high = Decimal(str(trade.highest_high)) if trade.highest_high is not None else entry
    return sr.trail_from_db(entry, stopdist, current_stop, highest_high, params=params)


def _slippage_for(bars, risk: RiskParams) -> Decimal:
    win = [float(b.close) * b.volume for b in bars[-60:]]
    return risk.slippage_for((median(win) / 1e7) if win else 0.0)


def _atr_at(bars) -> Optional[float]:
    if len(bars) < 20:
        return None
    val = precompute_features(bars)["atr"].to_numpy()[-1]
    return float(val) if val == val else None    # NaN -> None


def _close_trade(trade: Trade, fill_price: Decimal, exit_date: date, reason: str, stopdist: Decimal) -> None:
    qty = trade.remaining_qty or trade.total_qty or 0
    entry = Decimal(str(trade.avg_entry_price))
    trade.exit_price = fill_price
    trade.exit_date = exit_date
    trade.exit_qty = qty
    trade.exit_method = f"V2_{reason}"            # V2_CLOSE | V2_GAP
    trade.status = "CLOSED"
    trade.remaining_qty = 0
    trade.gross_pnl = (fill_price - entry) * Decimal(qty)
    if stopdist and stopdist != 0:
        trade.r_multiple = Decimal(str(round(float((fill_price - entry) / stopdist), 4)))


def run_eod_exits(db: Session, con: sqlite3.Connection, *, as_of: Optional[date] = None,
                  params: StrategyParams = STRATEGY_V2, risk: RiskParams = RISK_V2) -> dict:
    """Post-close pass: exit on a close-below, else ratchet + persist each open trail."""
    summary = {"checked": 0, "exited": 0, "trailed": 0}
    for trade in db.query(Trade).filter(Trade.status.in_(_OPEN)).all():
        bars = _bars_as_of(con, trade.symbol, as_of)
        trail = _trail_for(trade, params)
        if not bars or trail is None:
            continue
        summary["checked"] += 1
        bar = bars[-1]
        dec = sr.eod_exit(trail, bar, _atr_at(bars), slippage=_slippage_for(bars, risk))
        if dec.exited:
            _close_trade(trade, dec.fill_price, bar.date, dec.reason, trail.stopdist)
            summary["exited"] += 1
        else:
            trade.current_stop = trail.stop          # persist the ratcheted trail
            trade.highest_high = trail.highest_high
            summary["trailed"] += 1
    db.commit()
    return summary


def run_morning_gap_exits(db: Session, con: sqlite3.Connection, *, as_of: Optional[date] = None,
                          params: StrategyParams = STRATEGY_V2, risk: RiskParams = RISK_V2) -> dict:
    """09:15 pass: exit any open position that gaps open below its stop."""
    summary = {"checked": 0, "exited": 0}
    for trade in db.query(Trade).filter(Trade.status.in_(_OPEN)).all():
        bars = _bars_as_of(con, trade.symbol, as_of)
        trail = _trail_for(trade, params)
        if not bars or trail is None:
            continue
        summary["checked"] += 1
        dec = sr.morning_gap_exit(trail, bars[-1].open, slippage=_slippage_for(bars, risk))
        if dec is not None and dec.exited:
            _close_trade(trade, dec.fill_price, bars[-1].date, dec.reason, trail.stopdist)
            summary["exited"] += 1
    db.commit()
    return summary
