"""
rs_ema_strategy.py — RS EMA50×200 Live Paper Trading Engine (Dual Portfolio)

Entry : RS EMA50 crosses ABOVE RS EMA200 (golden cross on RS ratio)
Exit  : RS EMA50 drops BELOW RS EMA200  OR  10% hard stop from entry
Capital: ₹10,00,000 per portfolio | SL: 10% | Max positions: 15 each
Universe: NSE stocks with ADT ≥ ₹5cr (last 60 trading days)

Two portfolios run in parallel:
  Portfolio A — fills first with top RS-strength signals
  Portfolio B — mirrors A when ≤15 signals; takes overflow when >15
                (ensures all signals are covered across both, up to 30 unique)

The daily job runs at 16:30 IST (after market close).
All state is persisted in simulation_runs + simulation_trades tables.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from backend.config import settings
from backend.data.nse_stocks import NSE_UNIVERSE
from backend.database import SessionLocal, SimulationRun, SimulationTrade
from backend.services.notifications import send_telegram_message

logger = logging.getLogger(__name__)

# ── Strategy constants ─────────────────────────────────────────────────────────
CAPITAL       = 1_000_000.0  # ₹10,00,000 per portfolio
RPT           = 0.5          # % risk per trade
SL_PCT        = 10.0         # hard stop from entry (%)
MAX_POS       = 15           # maximum concurrent positions per portfolio
FAST_N        = 50           # RS EMA span
SLOW_N        = 200          # RS EMA span
MIN_ADT_CR    = 5.0          # minimum avg daily turnover (crore)
ADT_THRESHOLD = MIN_ADT_CR * 1e7
BUFFER_DAYS   = 370

RUN_NAME_A = "RS-EMA50x200-LIVE-A"
RUN_NAME_B = "RS-EMA50x200-LIVE-B"

# Position size per trade: Capital × RPT% / SL% = ₹10L × 0.5% / 10% = ₹50,000
POS_VALUE = CAPITAL * (RPT / 100) / (SL_PCT / 100)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def _get_or_create_run(db, name: str) -> SimulationRun:
    """Return the active run for the given portfolio name, or create a fresh one."""
    run = (
        db.query(SimulationRun)
        .filter(SimulationRun.name == name, SimulationRun.status == "ACTIVE")
        .first()
    )
    if run:
        return run

    run = SimulationRun(
        run_type="PAPER",
        name=name,
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
    label = "A" if name == RUN_NAME_A else "B"
    logger.info(f"[RS-EMA-{label}] Created new paper run id={run.id}")
    return run


# ── Data fetching ──────────────────────────────────────────────────────────────

def _fetch_data_sync() -> tuple[pd.Series, dict[str, pd.DataFrame]]:
    """Read BUFFER_DAYS of OHLCV for Nifty 50 + NSE stocks from the Kite bar store.

    Reads from the pre-ingested SQLite bar store (settings.bars_db_path), which is
    kept fresh by the corpus_updater job via KiteHistoricalAdapter. No network calls.
    """
    bars_path = settings.bars_db_path
    if not os.path.exists(bars_path):
        raise RuntimeError(
            f"Bar store not found at {bars_path}. "
            "Run scripts/ingest_kite_daily.py or wait for the corpus_updater job."
        )

    cutoff = (datetime.now() - timedelta(days=BUFFER_DAYS)).strftime("%Y-%m-%d")
    logger.info(f"[RS-EMA] Reading bar store {bars_path} from {cutoff}")

    con = sqlite3.connect(bars_path)
    try:
        # ── NIFTY 50 index closes ────────────────────────────────────────────
        rows = con.execute(
            "SELECT date, close FROM index_bars "
            "WHERE index_code='NIFTY 50' AND date >= ? ORDER BY date",
            (cutoff,),
        ).fetchall()
        if not rows:
            raise RuntimeError(
                "No 'NIFTY 50' rows in index_bars. "
                "Run scripts/ingest_kite_daily.py to populate the bar store."
            )
        nifty_close = pd.Series(
            [float(r[1]) for r in rows],
            index=pd.to_datetime([r[0] for r in rows]),
        )
        logger.info(f"[RS-EMA] NIFTY 50: {len(nifty_close)} days")

        # ── Stock OHLCV (universe = symbols already in the store) ────────────
        available = {
            r[0]
            for r in con.execute("SELECT symbol FROM done WHERE n > 0").fetchall()
        }
        symbols = [s for s in NSE_UNIVERSE if s in available]
        logger.info(f"[RS-EMA] {len(symbols)} symbols available in bar store")

        stock_data: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            bar_rows = con.execute(
                "SELECT date, open, high, low, close, volume FROM bars "
                "WHERE symbol=? AND date >= ? ORDER BY date",
                (sym, cutoff),
            ).fetchall()
            if len(bar_rows) < SLOW_N + 10:
                continue
            idx = pd.to_datetime([r[0] for r in bar_rows])
            stock_data[sym] = pd.DataFrame(
                {
                    "Open":   [float(r[1]) for r in bar_rows],
                    "High":   [float(r[2]) for r in bar_rows],
                    "Low":    [float(r[3]) for r in bar_rows],
                    "Close":  [float(r[4]) for r in bar_rows],
                    "Volume": [int(r[5]) for r in bar_rows],
                },
                index=idx,
            )
    finally:
        con.close()

    logger.info(f"[RS-EMA] Loaded {len(stock_data)} stocks from bar store")
    return nifty_close, stock_data


# ── Signal computation ─────────────────────────────────────────────────────────

def _compute_signals(
    nifty_close: pd.Series,
    stock_data: dict[str, pd.DataFrame],
) -> dict[str, dict]:
    signals: dict[str, dict] = {}

    for sym, df in stock_data.items():
        try:
            common = df.index.intersection(nifty_close.index)
            if len(common) < SLOW_N + 10:
                continue

            sc  = df.loc[common, "Close"].astype(float)
            vol = df.loc[common, "Volume"].astype(float)

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

    logger.info(f"[RS-EMA] Signals: {len(signals)} stocks pass ADT filter")
    return signals


# ── Equity calculator ─────────────────────────────────────────────────────────

def _compute_equity(
    db,
    run_id: int,
    open_positions: list[SimulationTrade],
    signals: dict[str, dict],
) -> tuple[float, float]:
    """Returns (cash, equity) for a portfolio given open positions and live prices."""
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


# ── Signal distribution between two portfolios ────────────────────────────────

def _distribute_entries(
    golden_signals: list[str],
    open_symbols_a: set[str],
    open_symbols_b: set[str],
    slots_a: int,
    slots_b: int,
    signals: dict[str, dict],
) -> tuple[list[str], list[str]]:
    """
    Distribute golden cross signals between Portfolio A and B.

    Rules:
    - Sort all signals by RS strength (strongest first)
    - A fills its available slots with the top signals
    - B: overflow signals A couldn't take come first (unique coverage),
          then fill remaining B slots from A's signal set (mirror)

    Examples (A and B both start fresh with 15 slots each):
    - 15 signals → A: 1-15, B: 1-15 (same 15, full mirror)
    - 20 signals → A: 1-15, B: 1-10 + 16-20 (B has 5 unique, 10 shared)
    - 30 signals → A: 1-15, B: 16-30 (completely different, all 30 covered)
    """
    all_sorted = sorted(
        golden_signals,
        key=lambda s: signals[s]["fast_curr"] / signals[s]["slow_curr"],
        reverse=True,
    )

    new_for_a = [s for s in all_sorted if s not in open_symbols_a]
    new_for_b = [s for s in all_sorted if s not in open_symbols_b]

    entries_a = new_for_a[:slots_a]
    set_a     = set(entries_a)

    # B: overflow (signals not taken by A) fills first, then mirror A
    overflow        = [s for s in new_for_b if s not in set_a]
    overflow_count  = min(len(overflow), slots_b)
    common_count    = max(0, slots_b - overflow_count)
    common_for_b    = [s for s in entries_a if s in set(new_for_b)][:common_count]
    entries_b       = common_for_b + overflow[:overflow_count]

    return entries_a, entries_b


# ── Exit processor (shared for both portfolios) ────────────────────────────────

def _process_exits(
    db, run: SimulationRun, signals: dict[str, dict], label: str
) -> tuple[list[str], list[SimulationTrade]]:
    """Process exits for one portfolio. Returns (exit_messages, remaining_open_positions)."""
    open_pos = (
        db.query(SimulationTrade)
        .filter(SimulationTrade.run_id == run.id, SimulationTrade.status.in_(["OPEN", "PARTIAL"]))
        .all()
    )

    exit_messages: list[str] = []
    for pos in open_pos:
        sig = signals.get(pos.symbol)
        if sig is None:
            continue

        remaining   = pos.remaining_qty or 0
        if remaining <= 0:
            continue

        entry_price = float(pos.entry_price or 0)
        sl_price    = float(pos.sl_price or entry_price * (1 - SL_PCT / 100))
        today_low   = sig["low"]
        today_open  = sig["open"]
        today_close = sig["close"]
        rs_above    = sig["rs_above"]

        exit_price  = None
        exit_reason = None

        if today_low <= sl_price:
            exit_price  = min(today_open, sl_price)
            exit_reason = "STOP_LOSS"
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
        pos.exit_date     = date.today()
        pos.gross_pnl     = round(pnl, 2)
        pos.r_multiple    = round(r_multiple, 2)
        pos.pnl_pct       = round(pnl_pct, 2)

        msg = (
            f"{pos.symbol}: {exit_reason} @ ₹{exit_price:.2f} "
            f"(entry ₹{entry_price:.2f}, {remaining} qty) "
            f"P&L ₹{pnl:+.0f} ({pnl_pct:+.1f}%, {r_multiple:+.2f}R)"
        )
        exit_messages.append(msg)
        logger.info(f"[RS-EMA-{label}] EXIT: {msg}")

    db.commit()

    remaining_open = (
        db.query(SimulationTrade)
        .filter(SimulationTrade.run_id == run.id, SimulationTrade.status.in_(["OPEN", "PARTIAL"]))
        .all()
    )
    return exit_messages, remaining_open


# ── Entry processor (one portfolio) ───────────────────────────────────────────

def _process_entries(
    db, run: SimulationRun, open_pos: list[SimulationTrade],
    entry_list: list[str], signals: dict[str, dict], label: str,
) -> tuple[list[str], float]:
    """Buy from entry_list. Returns (entry_messages, cash_spent)."""
    _, equity = _compute_equity(db, run.id, open_pos, signals)
    cash = CAPITAL + sum(float(t.gross_pnl or 0) for t in
                         db.query(SimulationTrade)
                         .filter(SimulationTrade.run_id == run.id, SimulationTrade.status == "CLOSED")
                         .all()) - sum(
        float(p.entry_price or 0) * (p.total_qty or 0) for p in open_pos
    )

    entry_messages: list[str] = []
    today = date.today()

    for sym in entry_list:
        sig         = signals[sym]
        entry_price = sig["close"]
        if entry_price <= 0:
            continue

        qty  = max(1, int(POS_VALUE / entry_price))
        cost = qty * entry_price

        if cost > cash:
            logger.info(f"[RS-EMA-{label}] Skip {sym}: cash ₹{cash:.0f} < cost ₹{cost:.0f}")
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
        entry_messages.append(msg)
        logger.info(f"[RS-EMA-{label}] ENTRY: {msg}")

    db.commit()
    return entry_messages, cash


# ── Run summary updater ────────────────────────────────────────────────────────

def _update_run_summary(db, run: SimulationRun, signals: dict[str, dict]) -> tuple[float, int]:
    """Refresh equity curve and aggregate stats on the run record. Returns (equity, open_count)."""
    open_pos = (
        db.query(SimulationTrade)
        .filter(SimulationTrade.run_id == run.id, SimulationTrade.status.in_(["OPEN", "PARTIAL"]))
        .all()
    )
    _, equity = _compute_equity(db, run.id, open_pos, signals)

    today = date.today()
    curve = json.loads(run.equity_curve) if run.equity_curve else []
    if curve and curve[-1]["date"] == today.isoformat():
        curve[-1]["equity"] = round(equity, 2)
    else:
        curve.append({"date": today.isoformat(), "equity": round(equity, 2)})
    run.equity_curve = json.dumps(curve)

    all_trades   = db.query(SimulationTrade).filter(SimulationTrade.run_id == run.id).all()
    closed_all   = [t for t in all_trades if t.status == "CLOSED"]
    wins         = [t for t in closed_all if float(t.gross_pnl or 0) > 0]

    run.final_capital    = round(equity, 2)
    run.total_pnl        = round(equity - CAPITAL, 2)
    run.total_return_pct = round((equity - CAPITAL) / CAPITAL * 100, 2)
    run.total_trades     = len(all_trades)
    run.win_count        = len(wins)
    run.loss_count       = len(closed_all) - len(wins)
    run.win_rate         = round(len(wins) / len(closed_all) * 100, 2) if closed_all else None
    run.last_processed_date = today
    run.updated_at       = datetime.now().isoformat()
    db.commit()

    return round(equity, 2), len(open_pos)


# ── Main daily job ─────────────────────────────────────────────────────────────

async def run_rs_ema_daily() -> dict:
    """
    Called by APScheduler at 16:30 IST every weekday.
    Fetches data once, then processes exits and entries for both Portfolio A and B.
    """
    today  = date.today()
    db     = SessionLocal()
    summary: dict = {
        "date": today.isoformat(),
        "A":    {"exits": [], "entries": [], "open_positions": 0, "equity": 0.0},
        "B":    {"exits": [], "entries": [], "open_positions": 0, "equity": 0.0},
        "errors": [],
    }

    try:
        run_a = _get_or_create_run(db, RUN_NAME_A)
        run_b = _get_or_create_run(db, RUN_NAME_B)

        # ── Fetch market data (shared by both portfolios) ────────────────────
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

        # ── Process exits (each portfolio independently) ─────────────────────
        exits_a, open_a = _process_exits(db, run_a, signals, "A")
        exits_b, open_b = _process_exits(db, run_b, signals, "B")

        summary["A"]["exits"] = exits_a
        summary["B"]["exits"] = exits_b

        # ── Collect golden cross signals ──────────────────────────────────────
        open_syms_a = {p.symbol for p in open_a}
        open_syms_b = {p.symbol for p in open_b}
        slots_a     = max(0, MAX_POS - len(open_a))
        slots_b     = max(0, MAX_POS - len(open_b))

        all_golden = [sym for sym, sig in signals.items() if sig["is_golden"]]
        logger.info(
            f"[RS-EMA] {len(all_golden)} golden cross signal(s) today | "
            f"A slots: {slots_a}, B slots: {slots_b}"
        )

        entries_a, entries_b = _distribute_entries(
            all_golden, open_syms_a, open_syms_b, slots_a, slots_b, signals
        )

        # ── Execute entries ───────────────────────────────────────────────────
        msgs_a, _ = _process_entries(db, run_a, open_a, entries_a, signals, "A")
        msgs_b, _ = _process_entries(db, run_b, open_b, entries_b, signals, "B")

        summary["A"]["entries"] = msgs_a
        summary["B"]["entries"] = msgs_b

        # ── Update run summaries ──────────────────────────────────────────────
        eq_a, cnt_a = _update_run_summary(db, run_a, signals)
        eq_b, cnt_b = _update_run_summary(db, run_b, signals)

        summary["A"]["equity"]         = eq_a
        summary["A"]["open_positions"] = cnt_a
        summary["B"]["equity"]         = eq_b
        summary["B"]["open_positions"] = cnt_b

        # ── Telegram alert ────────────────────────────────────────────────────
        await _send_daily_alert(summary, eq_a, eq_b)

    except Exception as e:
        logger.error(f"[RS-EMA] Daily job failed: {e}", exc_info=True)
        summary["errors"].append(str(e))
        db.rollback()
    finally:
        db.close()

    logger.info(
        f"[RS-EMA] Done — A: ₹{summary['A']['equity']:,.0f} "
        f"({summary['A']['open_positions']} open), "
        f"B: ₹{summary['B']['equity']:,.0f} ({summary['B']['open_positions']} open)"
    )
    return summary


# ── Telegram helper ────────────────────────────────────────────────────────────

async def _send_daily_alert(summary: dict, eq_a: float, eq_b: float) -> None:
    lines = [f"<b>RS EMA50×200 Paper Trading — {summary['date']}</b>"]

    for label in ("A", "B"):
        s = summary[label]
        pct = (s["equity"] - CAPITAL) / CAPITAL * 100
        lines.append(f"\n<b>── Portfolio {label} ──</b>")
        lines.append(f"Equity: ₹{s['equity']:,.0f} ({pct:+.1f}%) | {s['open_positions']} open")
        if s["exits"]:
            lines.append(f"🔴 Exits: {len(s['exits'])}")
            for m in s["exits"]:
                lines.append(f"  • {m}")
        if s["entries"]:
            lines.append(f"🟢 Entries: {len(s['entries'])}")
            for m in s["entries"]:
                lines.append(f"  • {m}")
        if not s["exits"] and not s["entries"]:
            lines.append("No entries or exits today.")

    if summary.get("errors"):
        lines.append(f"\n⚠️ Errors: {'; '.join(summary['errors'])}")

    await send_telegram_message("\n".join(lines))


# ── Read-only status queries ───────────────────────────────────────────────────

def _portfolio_status(db, run_name: str) -> dict:
    """Return status dict for one portfolio by run name."""
    run = (
        db.query(SimulationRun)
        .filter(SimulationRun.name == run_name)
        .order_by(SimulationRun.id.desc())
        .first()
    )
    if not run:
        return {"error": f"Portfolio {run_name} not started yet. POST /rs-strategy/run-now."}

    trades        = (db.query(SimulationTrade)
                      .filter(SimulationTrade.run_id == run.id)
                      .order_by(SimulationTrade.entry_date.desc())
                      .all())
    open_trades   = [t for t in trades if t.status in ("OPEN", "PARTIAL")]
    closed_trades = [t for t in trades if t.status == "CLOSED"]
    wins          = [t for t in closed_trades if float(t.gross_pnl or 0) > 0]
    losses        = [t for t in closed_trades if float(t.gross_pnl or 0) <= 0]
    total_pnl_c   = sum(float(t.gross_pnl or 0) for t in closed_trades)

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
            "total_pnl": round(total_pnl_c, 2),
            "wins":      len(wins),
            "losses":    len(losses),
            "win_rate":  round(len(wins) / len(closed_trades) * 100, 1) if closed_trades else None,
            "avg_win":   round(sum(float(t.gross_pnl or 0) for t in wins) / len(wins), 2) if wins else None,
            "avg_loss":  round(sum(float(t.gross_pnl or 0) for t in losses) / len(losses), 2) if losses else None,
        },
        "equity_curve": json.loads(run.equity_curve) if run.equity_curve else [],
    }


def _portfolio_trades(db, run_name: str) -> list[dict]:
    """Return trade ledger for one portfolio."""
    run = (
        db.query(SimulationRun)
        .filter(SimulationRun.name == run_name)
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


def get_both_portfolios_status() -> dict:
    """Return status for both Portfolio A and B."""
    db = SessionLocal()
    try:
        return {
            "A": _portfolio_status(db, RUN_NAME_A),
            "B": _portfolio_status(db, RUN_NAME_B),
        }
    finally:
        db.close()


def get_both_portfolios_trades() -> dict:
    """Return trade ledgers for both Portfolio A and B."""
    db = SessionLocal()
    try:
        return {
            "A": _portfolio_trades(db, RUN_NAME_A),
            "B": _portfolio_trades(db, RUN_NAME_B),
        }
    finally:
        db.close()
