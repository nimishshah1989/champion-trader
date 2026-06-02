"""Strategy runtime bridge — the ONE seam between the live app and the validated brain.

Every live job (daily scan, last-30-min entry, post-close exit, risk guard) calls THIS,
which delegates to the pure runtime (signal_service / exit_service / risk_manager) reading
bars from the market store. No trading rule or threshold lives here — only the two
live-vs-backtest adaptations the user signed off on:

  * ENTRY volume gate — the >=2x breakout-volume gate is finalised only at the close, but
    entries fire in the last 30 min. So we PROJECT full-day volume from volume-so-far and
    require the projection >= k x the 50-day average. (decision: project in the last 30 min.)
  * EXIT cadence — the close-based stop is evaluated ONCE on the official daily close, with
    a separate gap-down check at the 09:15 open. (decision: once-daily post-close + gap-check.)

It imports only the pure engine + the market store + sqlite — never FastAPI — so the whole
seam is unit-testable in isolation, and it is the single module the rest of the app needs
to run the validated strategy. The live services become thin callers of these functions.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from backend.engine.backtest_fast import load_bars
from backend.engine.fills import DEFAULT_SLIPPAGE
from backend.engine.kite_data import Bar
from backend.engine.runtime import exit_service, signal_service
from backend.engine.runtime.config import RISK_V2, STRATEGY_V2, RiskParams, StrategyParams
from backend.engine.runtime.exit_service import ExitDecision, TrailState
from backend.engine.runtime.risk_manager import bear_multiplier, position_size, update_halt
from backend.engine.runtime.signal_service import EntrySignal, Setup

NSE_SESSION_MINUTES = 375   # 09:15 -> 15:30


# --- DAILY SCAN (watchlist: pre-breakout SETUPS + tomorrow's trigger) ------------------

def scan_symbol(con: sqlite3.Connection, symbol: str, *, params: StrategyParams = STRATEGY_V2,
                as_of: Optional[date] = None) -> Optional[Setup]:
    """Is `symbol` a v2 SETUP as of its latest stored bar (or `as_of`)? Reads the market store.

    Returns the watchlist candidate (trigger for tomorrow + 1R stop). The breakout + >=2x
    volume confirmation happens live at the trigger break (`evaluate_live_entry`).
    """
    bars = load_bars(con, symbol)
    if as_of is not None:
        bars = [b for b in bars if b.date <= as_of]
    return signal_service.detect_setup(bars, params=params)


def scan_universe(con: sqlite3.Connection, symbols, *, params: StrategyParams = STRATEGY_V2,
                  as_of: Optional[date] = None) -> dict[str, Setup]:
    """Run the v2 SETUP scan across `symbols`; return only those that set up (the watchlist)."""
    out: dict[str, Setup] = {}
    for s in symbols:
        setup = scan_symbol(con, s, params=params, as_of=as_of)
        if setup is not None:
            out[s] = setup
    return out


# --- ENTRY (last 30 min): projected-volume gate + sizing -------------------------------

def project_full_day_volume(volume_so_far: float, minutes_elapsed: float,
                            session_minutes: float = NSE_SESSION_MINUTES) -> float:
    """Extrapolate the full session's volume from what has traded so far (flat-rate proxy)."""
    if minutes_elapsed <= 0:
        return 0.0
    return volume_so_far * (session_minutes / minutes_elapsed)


def breakout_volume_ok(volume_so_far: float, minutes_elapsed: float, vol_sma50: Optional[float],
                       *, params: StrategyParams = STRATEGY_V2,
                       session_minutes: float = NSE_SESSION_MINUTES) -> bool:
    """Will the projected full-day volume clear the >=k x 50-day-average breakout gate?"""
    if params.vol_breakout_k <= 0:
        return True                                  # gate disabled
    if not vol_sma50 or vol_sma50 <= 0:
        return False
    projected = project_full_day_volume(volume_so_far, minutes_elapsed, session_minutes)
    return projected >= params.vol_breakout_k * vol_sma50


def live_position_size(equity: Decimal, stopdist: Decimal, regime_on: bool,
                       open_positions: int, halted: bool, *, risk: RiskParams = RISK_V2) -> int:
    """Shares to buy for a live entry, after the portfolio gates. 0 = blocked or too small."""
    if halted or open_positions >= risk.max_positions:
        return 0
    return position_size(equity, stopdist, rpt_pct=risk.rpt_pct,
                         bear_mult=bear_multiplier(regime_on, risk))


@dataclass
class LiveEntry:
    shares: int
    entry_price: Decimal      # the live break/fill price
    stop: Decimal             # initial close-based stop = entry - 1R


def evaluate_live_entry(*, trigger: Decimal, stopdist: Decimal, last_price: Decimal,
                        volume_so_far: float, minutes_elapsed: float, vol_sma50: Optional[float],
                        equity: Decimal, open_positions: int, halted: bool, regime_on: bool,
                        params: StrategyParams = STRATEGY_V2, risk: RiskParams = RISK_V2,
                        session_minutes: float = NSE_SESSION_MINUTES) -> Optional[LiveEntry]:
    """Compose the last-30-min entry: trigger broken + projected volume + sized within risk."""
    if last_price < trigger:                          # the 5-day-high break hasn't happened yet
        return None
    if not breakout_volume_ok(volume_so_far, minutes_elapsed, vol_sma50,
                              params=params, session_minutes=session_minutes):
        return None
    shares = live_position_size(equity, stopdist, regime_on, open_positions, halted, risk=risk)
    if shares <= 0:
        return None
    return LiveEntry(shares=shares, entry_price=last_price, stop=last_price - stopdist)


# --- EXIT (once daily): trail persistence + the two live moments -----------------------

def open_trail(entry: Decimal, stopdist: Decimal, breakout_high: Decimal, *,
               params: StrategyParams = STRATEGY_V2) -> TrailState:
    """Open the chandelier trail at entry (stop = entry - 1R, peak = the breakout high)."""
    return exit_service.init_trail(entry, stopdist, breakout_high, params=params)


def trail_from_db(entry: Decimal, stopdist: Decimal, current_stop: Decimal, highest_high: Decimal,
                  *, params: StrategyParams = STRATEGY_V2) -> TrailState:
    """Rebuild a live position's trail from its persisted trades-table columns."""
    return TrailState(entry=entry, stopdist=stopdist, stop=current_stop,
                      highest_high=highest_high, mult=params.chandelier_mult)


def morning_gap_exit(trail: TrailState, day_open: Decimal, *,
                     slippage: Decimal = DEFAULT_SLIPPAGE) -> Optional[ExitDecision]:
    """09:15 gap-check: if the stock OPENS below the stop, exit at the open. Else hold."""
    if day_open <= trail.stop:
        bar = Bar(date.today(), day_open, day_open, day_open, day_open, 0)
        return exit_service.step(trail, bar, atr=None, slippage=slippage)
    return None


def eod_exit(trail: TrailState, daily_bar: Bar, atr: Optional[float], *,
             slippage: Decimal = DEFAULT_SLIPPAGE) -> ExitDecision:
    """Post-close evaluation on the official daily bar: exit on a close-below, else ratchet up."""
    return exit_service.step(trail, daily_bar, atr, slippage=slippage)
