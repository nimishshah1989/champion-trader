"""Post-close v2 entry job — the validated breakout entry on READY watchlist names.

Replaces the legacy alert→ladder buy path (`autopilot.auto_execute_buys` with its
2R/NE/GE/EE targets). Per the validated strategy it evaluates, on the latest daily bar,
whether a watchlist setup has broken its 5-day-high trigger WITH ≥2× breakout volume and
is not circuit-locked (the parity-proven `signal_service.evaluate_entry`), then sizes the
fill through the portfolio risk gate (`risk_manager` via the bridge: RPT 0.35%, max-15
cap, bear-0.25× when NIFTY 500 is below a rising 50-DMA, and the DD halt).

In PAPER mode the "live price" is the latest stored daily bar, so this runs once post-close
on the day's full-day volume — identical to the backtest entry. In LIVE mode the same gate
runs intraday in the last 30 min with *projected* volume (`strategy_runtime.
evaluate_live_entry`); the validated decision logic is shared. Each fill opens a Trade
carrying the chandelier trail columns (current_stop / highest_high / atr_at_entry) the exit
job reads back, plus a BUY ActionAlert for the audit trail + Telegram. Pure orchestration:
a DB session + a market-store connection in, trades + a summary out — no network, no
scheduler, no clock.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import ActionAlert, Trade, Watchlist
from backend.engine.backtest_fast import load_bars
from backend.engine.precompute import precompute_features
from backend.engine.regime import load_regime
from backend.engine.runtime.config import RISK_V2, STRATEGY_V2, RiskParams, StrategyParams
from backend.engine.runtime.signal_service import EntrySignal, evaluate_entry
from backend.services import strategy_runtime as sr

IST = ZoneInfo("Asia/Kolkata")
_OPEN = ("OPEN", "PARTIAL")


def _bars_as_of(con: sqlite3.Connection, symbol: str, as_of: Optional[date]) -> list:
    bars = load_bars(con, symbol)
    return [b for b in bars if as_of is None or b.date <= as_of]


def _regime_on(cache_path: str, as_of: Optional[date], risk: RiskParams) -> bool:
    """v2 risk-on flag: NIFTY 500 above a rising 50-DMA, as of `as_of` (else the latest)."""
    try:
        regime_on, _ = load_regime(cache_path, "NIFTY 500",
                                   risk.regime_sma_window, risk.regime_slope_lb)
    except Exception:
        return True                                  # no index data -> full size (paper only)
    if not regime_on:
        return True
    if as_of is not None and as_of in regime_on:
        return regime_on[as_of]
    days = [d for d in regime_on if as_of is None or d <= as_of]
    return regime_on[max(days)] if days else True


def _paper_equity(db: Session, start_capital: Decimal) -> Decimal:
    """Realised paper equity = start + Σ closed-trade gross P&L (compounds like the backtest)."""
    realised = Decimal("0")
    for t in db.query(Trade).filter(Trade.status == "CLOSED").all():
        if t.gross_pnl is not None:
            realised += Decimal(str(t.gross_pnl))
    return start_capital + realised


def run_entries(db: Session, con: sqlite3.Connection, *, as_of: Optional[date] = None,
                symbols: Optional[list[str]] = None, equity: Optional[Decimal] = None,
                halted: bool = False, params: StrategyParams = STRATEGY_V2,
                risk: RiskParams = RISK_V2, cache_path: Optional[str] = None) -> dict:
    """Post-close pass: open a v2 trade for any watchlist name that broke out on the day's bar."""
    cache_path = cache_path or settings.bars_db_path
    if symbols is None:
        symbols = [w.symbol for w in db.query(Watchlist)
                   .filter(Watchlist.bucket == "READY", Watchlist.status == "ACTIVE").all()]
    held = {t.symbol for t in db.query(Trade).filter(Trade.status.in_(_OPEN)).all()}
    open_positions = len(held)
    if equity is None:
        equity = _paper_equity(db, Decimal(str(settings.paper_capital)))
    regime_on = _regime_on(cache_path, as_of, risk)

    summary = {"checked": 0, "entered": 0, "blocked": 0, "opened": []}
    for sym in symbols:
        if sym in held:
            continue
        bars = _bars_as_of(con, sym, as_of)
        sig = evaluate_entry(bars, params=params)
        summary["checked"] += 1
        if sig is None:
            continue
        shares = sr.live_position_size(equity, sig.stopdist, regime_on,
                                       open_positions, halted, risk=risk)
        if shares <= 0:
            summary["blocked"] += 1                   # cap / halt / sub-1-share
            continue
        trade = _open_trade(db, sym, sig, shares, bars, as_of, regime_on, params)
        held.add(sym)
        open_positions += 1
        summary["entered"] += 1
        summary["opened"].append(
            {"symbol": sym, "shares": shares, "entry": sig.entry, "stop": trade.current_stop})
    db.commit()
    return summary


def _open_trade(db: Session, symbol: str, sig: EntrySignal, shares: int, bars: list,
                as_of: Optional[date], regime_on: bool, params: StrategyParams) -> Trade:
    """Open a v2 Trade with the chandelier trail seeded + the attribution snapshot, and log a BUY."""
    entry, stopdist = sig.entry, sig.stopdist
    trail = sr.open_trail(entry, stopdist, bars[-1].high, params=params)
    df = precompute_features(bars)
    atr = df["atr"].to_numpy()[-1]
    stage = str(df["stage"].to_numpy()[-2]) if len(bars) >= 2 else None
    avg_trp = Decimal(str(sig.avg_trp))

    trade = Trade(
        symbol=symbol,
        entry_date=as_of or bars[-1].date,
        entry_type="V2_BREAK",
        avg_entry_price=entry,
        entry_price_half1=entry,
        qty_half1=shares,                             # v2 = single entry (no 50/50 ladder split)
        total_qty=shares,
        remaining_qty=shares,
        trp_at_entry=avg_trp,
        sl_price=trail.stop,
        sl_pct=avg_trp,
        rpt_amount=stopdist * Decimal(shares),
        status="OPEN",
        setup_type="V2_AUTO",
        # --- v2 chandelier trail (seeded; ratcheted by exit_runtime) ---
        current_stop=trail.stop,
        highest_high=trail.highest_high,
        atr_at_entry=(Decimal(str(round(float(atr), 4))) if atr == atr else None),
        # --- attribution snapshot ---
        signal_type=stage,
        regime_at_entry="bull" if regime_on else "bear",
        volume_ratio_at_entry=(Decimal(str(round(sig.volume_ratio, 4)))
                               if sig.volume_ratio == sig.volume_ratio else None),
        avg_trp_at_entry=avg_trp,
        strategy_version=params.version,
        entry_notes=(f"v2 paper entry: break {sig.trigger}, vol {sig.volume_ratio:.2f}x, "
                     f"size {shares} @ {entry}, SL {trail.stop}"),
    )
    db.add(trade)
    db.flush()                                        # assign trade.id for the alert FK
    db.add(ActionAlert(
        alert_category="BUY",
        alert_type="V2_BREAK",
        symbol=symbol,
        current_price=entry,
        trigger_price=sig.trigger,
        suggested_entry_price=entry,
        suggested_qty=shares,
        suggested_sl_price=trail.stop,
        trp_pct=avg_trp,
        status="ACTED",
        acted_at=datetime.now(tz=IST),
        resulting_trade_id=trade.id,
        source="V2_ENTRY",
        action_text=f"BUY {shares} {symbol} @ ₹{entry} (break ₹{sig.trigger}, SL ₹{trail.stop})",
    ))
    return trade
