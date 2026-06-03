"""
rs_ema_strategy.py — RS EMA50×200 Live Paper Trading Engine

Entry : RS EMA50 crosses ABOVE RS EMA200 (golden cross on RS ratio)
Exit  : RS EMA50 drops BELOW RS EMA200  OR  10% hard stop from entry
Capital: ₹1,00,000 | RPT: 0.5% | SL: 10% | Max positions: 15
Universe: NSE stocks with ADT ≥ ₹5cr (last 60 trading days)

The daily job runs at 16:30 IST (after market close).
Positions are entered at today's closing price (paper trading simplification).
All state is persisted in simulation_runs + simulation_trades tables.
"""

from __future__ import annotations

import asyncio
import json
import logging
import warnings
from datetime import date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import yfinance as yf

from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix
from backend.database import SessionLocal, SimulationRun, SimulationTrade
from backend.services.notifications import send_telegram_message

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ── Strategy constants ─────────────────────────────────────────────────────────
CAPITAL       = 100_000.0   # ₹1,00,000 starting capital
RPT           = 0.5         # % risk per trade
SL_PCT        = 10.0        # hard stop from entry (%)
MAX_POS       = 15          # maximum concurrent positions
FAST_N        = 50          # RS EMA span
SLOW_N        = 200         # RS EMA span
MIN_ADT_CR    = 5.0         # minimum avg daily turnover (crore)
ADT_THRESHOLD = MIN_ADT_CR * 1e7   # 5 crore = ₹5,00,00,000
BUFFER_DAYS   = 370         # history fetch window (>200 trading days + weekends)
BATCH_SIZE    = 50
RUN_NAME      = "RS-EMA50x200-LIVE"

# Fixed position value per trade (₹5,000)
POS_VALUE = CAPITAL * (RPT / 100) / (SL_PCT / 100)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def _get_or_create_run(db) -> SimulationRun:
    """Return the active RS-EMA run, or create a fresh one."""
    run = (
        db.query(SimulationRun)
        .filter(SimulationRun.name == RUN_NAME, SimulationRun.status == "ACTIVE")
        .first()
    )
    if run:
        return run

    run = SimulationRun(
        run_type="PAPER",
        name=RUN_NAME,
        starting_capital=CAPITAL,
        rpt_pct=RPT,
        start_date=date.today(),
        status="ACTIVE",
        final_capital=CAPITAL,
        total_pnl=0,
        total_return_pct=0,
        total_trades=0,
        win_count=0,
        loss_count=0,
        equity_curve=json.dumps([{"date": date.today().isoformat(), "equity": CAPITAL}]),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info(f"[RS-EMA] Created new paper run id={run.id}")
    return run


# ── Data fetching (synchronous — called via asyncio.to_thread) ─────────────────

def _fetch_data_sync() -> tuple[pd.Series, dict[str, pd.DataFrame]]:
    """
    Download the last BUFFER_DAYS of OHLCV for Nifty 50 and all NSE stocks.
    Returns (nifty_close Series, {symbol: OHLCV DataFrame}).
    """
    end_dt = datetime.now()
    start_str = (end_dt - timedelta(days=BUFFER_DAYS)).strftime("%Y-%m-%d")
    end_str   = end_dt.strftime("%Y-%m-%d")

    logger.info(f"[RS-EMA] Fetching data {start_str} → {end_str}")

    # Nifty 50 benchmark
    nifty_raw = yf.download("^NSEI", start=start_str, end=end_str,
                             auto_adjust=True, progress=False, timeout=60)
    if isinstance(nifty_raw.columns, pd.MultiIndex):
        nifty_raw.columns = [c[0] for c in nifty_raw.columns]
    nifty_raw.index = pd.to_datetime(nifty_raw.index).normalize()
    nifty_close = nifty_raw["Close"].astype(float).dropna()
    logger.info(f"[RS-EMA] NIFTY: {len(nifty_close)} days")

    # NSE universe in batches
    all_symbols = get_yfinance_symbols()
    stock_data: dict[str, pd.DataFrame] = {}
    batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]

    for bi, batch in enumerate(batches):
        logger.info(f"[RS-EMA] Batch {bi + 1}/{len(batches)}")
        try:
            raw = yf.download(
                tickers=batch, start=start_str, end=end_str,
                group_by="ticker", auto_adjust=True,
                threads=True, progress=False, timeout=120,
            )
            if raw.empty:
                continue
            for sym in batch:
                clean = strip_ns_suffix(sym)
                try:
                    if len(batch) > 1 and isinstance(raw.columns, pd.MultiIndex):
                        df = raw[sym].copy()
                    else:
                        df = raw.copy()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = [c[0] for c in df.columns]
                    df = df.dropna(subset=["Close"])
                    df.index = pd.to_datetime(df.index).normalize()
                    if len(df) >= 210:
                        stock_data[clean] = df[["Open", "High", "Low", "Close", "Volume"]]
                except (KeyError, TypeError):
                    pass
        except Exception as e:
            logger.error(f"[RS-EMA] Batch {bi + 1} error: {e}")

    logger.info(f"[RS-EMA] Fetched {len(stock_data)} stocks")
    return nifty_close, stock_data


# ── Signal computation ─────────────────────────────────────────────────────────

def _compute_signals(
    nifty_close: pd.Series,
    stock_data: dict[str, pd.DataFrame],
) -> dict[str, dict]:
    """
    Compute RS EMA50 / EMA200 for every stock and classify today's status.

    Returned dict shape per symbol:
      close, open, low  — today's OHLCV values
      fast_prev/curr    — EMA50 on RS, yesterday and today
      slow_prev/curr    — EMA200 on RS, yesterday and today
      is_golden         — golden cross today (EMA50 crossed above EMA200)
      is_death          — death cross today  (EMA50 crossed below  EMA200)
      rs_above          — True if EMA50 currently above EMA200
    """
    signals: dict[str, dict] = {}

    for sym, df in stock_data.items():
        try:
            common = df.index.intersection(nifty_close.index)
            if len(common) < SLOW_N + 10:
                continue

            sc  = df.loc[common, "Close"].astype(float)
            vol = df.loc[common, "Volume"].astype(float)

            # ADT filter: last 60 available trading days
            adt = (sc * vol).iloc[-60:].mean()
            if np.isnan(adt) or adt < ADT_THRESHOLD:
                continue

            nc   = nifty_close.loc[common].astype(float)
            rs   = sc / nc
            fast = _ema(rs, FAST_N)
            slow = _ema(rs, SLOW_N)

            if len(fast) < 2:
                continue

            fc, fp = float(fast.iloc[-1]), float(fast.iloc[-2])
            sc2, sp = float(slow.iloc[-1]), float(slow.iloc[-2])

            if any(np.isnan(v) for v in [fc, fp, sc2, sp]):
                continue

            signals[sym] = {
                "close":     float(sc.iloc[-1]),
                "open":      float(df.loc[common, "Open"].iloc[-1]),
                "low":       float(df.loc[common, "Low"].iloc[-1]),
                "fast_prev": fp,
                "slow_prev": sp,
                "fast_curr": fc,
                "slow_curr": sc2,
                "is_golden": fp <= sp and fc > sc2,
                "is_death":  fp >= sp and fc < sc2,
                "rs_above":  fc > sc2,
            }
        except Exception:
            pass

    logger.info(f"[RS-EMA] Signals computed: {len(signals)} stocks pass ADT filter")
    return signals


# ── Equity calculator ─────────────────────────────────────────────────────────

def _compute_equity(
    db,
    run_id: int,
    open_positions: list[SimulationTrade],
    signals: dict[str, dict],
) -> tuple[float, float]:
    """
    Returns (cash, equity) given current open positions and live prices.
    """
    closed = (
        db.query(SimulationTrade)
        .filter(SimulationTrade.run_id == run_id, SimulationTrade.status == "CLOSED")
        .all()
    )
    realized_pnl = sum(float(t.gross_pnl or 0) for t in closed)
    invested = sum(float(p.entry_price or 0) * (p.total_qty or 0) for p in open_positions)
    mtm = sum(
        signals.get(p.symbol, {}).get("close", float(p.entry_price or 0))
        * (p.remaining_qty or 0)
        for p in open_positions
    )
    cash   = CAPITAL + realized_pnl - invested
    equity = cash + mtm
    return cash, equity


# ── Main daily job ─────────────────────────────────────────────────────────────

async def run_rs_ema_daily() -> dict:
    """
    Called by APScheduler at 16:30 IST every weekday.
    Fetches data, detects crosses, processes exits then entries, updates DB.
    """
    today = date.today()
    db = SessionLocal()
    summary: dict = {
        "date":           today.isoformat(),
        "exits":          [],
        "entries":        [],
        "open_positions": 0,
        "equity":         0.0,
        "errors":         [],
    }

    try:
        run = _get_or_create_run(db)

        # Fetch prices in a thread (yfinance is blocking)
        try:
            nifty_close, stock_data = await asyncio.to_thread(_fetch_data_sync)
        except Exception as e:
            summary["errors"].append(f"Data fetch failed: {e}")
            logger.error(f"[RS-EMA] Data fetch failed: {e}", exc_info=True)
            return summary

        signals = _compute_signals(nifty_close, stock_data)
        if not signals:
            summary["errors"].append("No signals computed — market data unavailable?")
            return summary

        # ── Process exits ────────────────────────────────────────────────────
        open_pos = (
            db.query(SimulationTrade)
            .filter(
                SimulationTrade.run_id == run.id,
                SimulationTrade.status.in_(["OPEN", "PARTIAL"]),
            )
            .all()
        )

        exit_messages: list[str] = []
        for pos in open_pos:
            sig = signals.get(pos.symbol)
            if sig is None:
                continue  # no data today — keep holding

            remaining    = pos.remaining_qty or 0
            if remaining <= 0:
                continue

            entry_price  = float(pos.entry_price or 0)
            sl_price     = float(pos.sl_price or entry_price * (1 - SL_PCT / 100))
            today_low    = sig["low"]
            today_open   = sig["open"]
            today_close  = sig["close"]
            rs_above     = sig["rs_above"]

            exit_price  = None
            exit_reason = None

            # Stop loss: today's low touched or breached the stop
            if today_low <= sl_price:
                # Gap-down fills at open; normal fills at stop
                exit_price  = min(today_open, sl_price)
                exit_reason = "STOP_LOSS"
            # RS cross: EMA50 now below EMA200 (includes fresh death cross)
            elif not rs_above:
                exit_price  = today_close
                exit_reason = "RS_DEATH_CROSS"

            if exit_price is None:
                continue

            pnl        = (exit_price - entry_price) * remaining
            trp_value  = entry_price * (SL_PCT / 100)
            r_multiple = (exit_price - entry_price) / trp_value if trp_value else 0
            pnl_pct    = ((exit_price - entry_price) / entry_price * 100) if entry_price else 0

            if exit_reason == "STOP_LOSS":
                pos.qty_exited_sl    = remaining
            else:
                pos.qty_exited_final = remaining

            pos.remaining_qty = 0
            pos.status        = "CLOSED"
            pos.exit_date     = today
            pos.gross_pnl     = round(pnl, 2)
            pos.r_multiple    = round(r_multiple, 2)
            pos.pnl_pct       = round(pnl_pct, 2)

            msg = (
                f"{pos.symbol}: {exit_reason} @ ₹{exit_price:.2f} "
                f"(entry ₹{entry_price:.2f}, {remaining} qty) "
                f"P&L ₹{pnl:+.0f} ({pnl_pct:+.1f}%, {r_multiple:+.2f}R)"
            )
            summary["exits"].append(msg)
            exit_messages.append(msg)
            logger.info(f"[RS-EMA] EXIT: {msg}")

        db.commit()

        # ── Refresh open positions after exits ───────────────────────────────
        open_pos = (
            db.query(SimulationTrade)
            .filter(
                SimulationTrade.run_id == run.id,
                SimulationTrade.status.in_(["OPEN", "PARTIAL"]),
            )
            .all()
        )
        open_symbols = {p.symbol for p in open_pos}
        cash, equity = _compute_equity(db, run.id, open_pos, signals)

        # ── Process entries — golden crosses today ───────────────────────────
        golden_today = [
            sym for sym, sig in signals.items()
            if sig["is_golden"] and sym not in open_symbols
        ]
        # Sort by RS ratio strength (higher fast EMA relative to slow = stronger cross)
        golden_today.sort(
            key=lambda s: signals[s]["fast_curr"] / signals[s]["slow_curr"],
            reverse=True,
        )

        entry_messages: list[str] = []
        for sym in golden_today:
            if len(open_pos) + len(entry_messages) >= MAX_POS:
                break

            sig         = signals[sym]
            entry_price = sig["close"]
            if entry_price <= 0:
                continue

            qty  = max(1, int(POS_VALUE / entry_price))
            cost = qty * entry_price

            if cost > cash:
                logger.info(f"[RS-EMA] Skip {sym}: cash ₹{cash:.0f} < cost ₹{cost:.0f}")
                continue

            sl_price   = entry_price * (1 - SL_PCT / 100)
            rpt_amount = CAPITAL * (RPT / 100)

            sim_trade = SimulationTrade(
                run_id=run.id,
                symbol=sym,
                signal_date=today,
                entry_date=today,
                entry_price=round(entry_price, 2),
                total_qty=qty,
                half_qty=max(1, qty // 2),
                trp_pct=SL_PCT,
                sl_price=round(sl_price, 2),
                rpt_amount=round(rpt_amount, 2),
                remaining_qty=qty,
                status="OPEN",
                portfolio_value_at_entry=round(equity, 2),
            )
            db.add(sim_trade)
            cash -= cost

            msg = (
                f"{sym}: GOLDEN CROSS @ ₹{entry_price:.2f} "
                f"({qty} qty, ₹{cost:.0f}) SL ₹{sl_price:.2f}"
            )
            summary["entries"].append(msg)
            entry_messages.append(msg)
            logger.info(f"[RS-EMA] ENTRY: {msg}")

        db.commit()

        # ── Update equity curve and run summary ──────────────────────────────
        open_pos = (
            db.query(SimulationTrade)
            .filter(
                SimulationTrade.run_id == run.id,
                SimulationTrade.status.in_(["OPEN", "PARTIAL"]),
            )
            .all()
        )
        cash, equity = _compute_equity(db, run.id, open_pos, signals)

        curve = json.loads(run.equity_curve) if run.equity_curve else []
        if curve and curve[-1]["date"] == today.isoformat():
            curve[-1]["equity"] = round(equity, 2)
        else:
            curve.append({"date": today.isoformat(), "equity": round(equity, 2)})
        run.equity_curve = json.dumps(curve)

        all_trades = (
            db.query(SimulationTrade)
            .filter(SimulationTrade.run_id == run.id)
            .all()
        )
        closed_all = [t for t in all_trades if t.status == "CLOSED"]
        wins       = [t for t in closed_all if float(t.gross_pnl or 0) > 0]

        run.final_capital       = round(equity, 2)
        run.total_pnl           = round(equity - CAPITAL, 2)
        run.total_return_pct    = round((equity - CAPITAL) / CAPITAL * 100, 2)
        run.total_trades        = len(all_trades)
        run.win_count           = len(wins)
        run.loss_count          = len(closed_all) - len(wins)
        run.win_rate            = round(len(wins) / len(closed_all) * 100, 2) if closed_all else None
        run.last_processed_date = today
        run.updated_at          = datetime.now().isoformat()
        db.commit()

        summary["open_positions"] = len(open_pos)
        summary["equity"]         = round(equity, 2)

        # ── Telegram alert ───────────────────────────────────────────────────
        await _send_daily_alert(summary, exit_messages, entry_messages, equity, open_pos)

    except Exception as e:
        logger.error(f"[RS-EMA] Daily job failed: {e}", exc_info=True)
        summary["errors"].append(str(e))
        db.rollback()
    finally:
        db.close()

    logger.info(
        f"[RS-EMA] Done — equity ₹{summary['equity']:,.0f}, "
        f"{len(summary['entries'])} entries, {len(summary['exits'])} exits"
    )
    return summary


# ── Telegram helper ────────────────────────────────────────────────────────────

async def _send_daily_alert(
    summary: dict,
    exits: list[str],
    entries: list[str],
    equity: float,
    open_pos: list[SimulationTrade],
) -> None:
    lines = [f"<b>RS EMA50×200 Paper Trading — {summary['date']}</b>"]

    if exits:
        lines.append(f"\n🔴 <b>EXITS ({len(exits)}):</b>")
        for m in exits:
            lines.append(f"  • {m}")

    if entries:
        lines.append(f"\n🟢 <b>NEW ENTRIES ({len(entries)}):</b>")
        for m in entries:
            lines.append(f"  • {m}")

    if not exits and not entries:
        lines.append("\nNo entries or exits today.")

    pct = (equity - CAPITAL) / CAPITAL * 100
    lines.append(
        f"\n<b>Portfolio: ₹{equity:,.0f} ({pct:+.1f}%)</b> "
        f"| {len(open_pos)} open positions"
    )

    if summary.get("errors"):
        lines.append(f"\n⚠️ Errors: {'; '.join(summary['errors'])}")

    await send_telegram_message("\n".join(lines))


# ── Read-only status queries ───────────────────────────────────────────────────

def get_portfolio_status() -> dict:
    """Return full portfolio status for the API endpoint."""
    db = SessionLocal()
    try:
        run = (
            db.query(SimulationRun)
            .filter(SimulationRun.name == RUN_NAME)
            .order_by(SimulationRun.id.desc())
            .first()
        )
        if not run:
            return {
                "error": "No RS EMA paper run found. POST /rs-strategy/run-now to initialise.",
            }

        trades = (
            db.query(SimulationTrade)
            .filter(SimulationTrade.run_id == run.id)
            .order_by(SimulationTrade.entry_date.desc())
            .all()
        )
        open_trades   = [t for t in trades if t.status in ("OPEN", "PARTIAL")]
        closed_trades = [t for t in trades if t.status == "CLOSED"]

        total_pnl_closed = sum(float(t.gross_pnl or 0) for t in closed_trades)
        wins  = [t for t in closed_trades if float(t.gross_pnl or 0) > 0]
        losses = [t for t in closed_trades if float(t.gross_pnl or 0) <= 0]

        return {
            "run_id":           run.id,
            "status":           run.status,
            "start_date":       run.start_date.isoformat() if run.start_date else None,
            "last_run_date":    run.last_processed_date.isoformat() if run.last_processed_date else None,
            "starting_capital": float(run.starting_capital),
            "current_equity":   float(run.final_capital or run.starting_capital),
            "total_pnl":        round(float(run.total_pnl or 0), 2),
            "total_return_pct": round(float(run.total_return_pct or 0), 2),
            "total_trades":     run.total_trades or 0,
            "win_count":        run.win_count or 0,
            "loss_count":       run.loss_count or 0,
            "win_rate":         float(run.win_rate) if run.win_rate else None,
            "open_positions":   len(open_trades),
            "config": {
                "capital":       CAPITAL,
                "rpt_pct":       RPT,
                "sl_pct":        SL_PCT,
                "max_positions": MAX_POS,
                "ema_fast":      FAST_N,
                "ema_slow":      SLOW_N,
                "min_adt_cr":    MIN_ADT_CR,
                "pos_value":     POS_VALUE,
            },
            "open_trades": [
                {
                    "symbol":         t.symbol,
                    "entry_date":     t.entry_date.isoformat() if t.entry_date else None,
                    "entry_price":    float(t.entry_price or 0),
                    "qty":            t.remaining_qty,
                    "sl_price":       float(t.sl_price or 0),
                    "position_value": round(float(t.entry_price or 0) * (t.remaining_qty or 0), 2),
                    "rpt_amount":     float(t.rpt_amount or 0),
                }
                for t in open_trades
            ],
            "closed_summary": {
                "count":     len(closed_trades),
                "total_pnl": round(total_pnl_closed, 2),
                "wins":      len(wins),
                "losses":    len(losses),
                "win_rate":  round(len(wins) / len(closed_trades) * 100, 1) if closed_trades else None,
                "avg_win":   round(
                    sum(float(t.gross_pnl or 0) for t in wins) / len(wins), 2
                ) if wins else None,
                "avg_loss":  round(
                    sum(float(t.gross_pnl or 0) for t in losses) / len(losses), 2
                ) if losses else None,
            },
            "equity_curve": json.loads(run.equity_curve) if run.equity_curve else [],
        }
    finally:
        db.close()


def get_all_trades() -> list[dict]:
    """Return full trade ledger for the API endpoint."""
    db = SessionLocal()
    try:
        run = (
            db.query(SimulationRun)
            .filter(SimulationRun.name == RUN_NAME)
            .order_by(SimulationRun.id.desc())
            .first()
        )
        if not run:
            return []

        trades = (
            db.query(SimulationTrade)
            .filter(SimulationTrade.run_id == run.id)
            .order_by(SimulationTrade.entry_date.desc())
            .all()
        )

        result = []
        for t in trades:
            entry_price = float(t.entry_price or 0)
            qty         = t.total_qty or 0
            remaining   = t.remaining_qty or 0

            if t.status == "CLOSED":
                if t.qty_exited_sl and t.qty_exited_sl > 0:
                    exit_reason = "STOP_LOSS"
                elif t.qty_exited_final and t.qty_exited_final > 0:
                    exit_reason = "RS_DEATH_CROSS"
                else:
                    exit_reason = "UNKNOWN"
            else:
                exit_reason = None

            result.append({
                "id":             t.id,
                "symbol":         t.symbol,
                "signal_date":    t.signal_date.isoformat() if t.signal_date else None,
                "entry_date":     t.entry_date.isoformat() if t.entry_date else None,
                "entry_price":    entry_price,
                "qty":            qty,
                "sl_price":       float(t.sl_price or 0),
                "rpt_amount":     float(t.rpt_amount or 0),
                "status":         t.status,
                "exit_date":      t.exit_date.isoformat() if t.exit_date else None,
                "exit_reason":    exit_reason,
                "gross_pnl":      float(t.gross_pnl or 0),
                "pnl_pct":        float(t.pnl_pct or 0),
                "r_multiple":     float(t.r_multiple or 0),
                "position_value": round(entry_price * qty, 2),
                "remaining_qty":  remaining,
            })

        return result
    finally:
        db.close()
