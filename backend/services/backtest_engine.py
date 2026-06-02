"""
Backtest engine — simulates the full Champion Trader system over a historical period.

⚠ LEGACY / UNVALIDATED. This is the OLD strategy: PPC/NPC setups on a yfinance feed
with the 2R/NE/GE/EE profit ladder — NOT the validated v2 engine (close-based 5×ATR
chandelier, ≥2× breakout-volume gate, RPT 0.35 + portfolio overlay). It is the second,
*unvalidated* backtester the rewire audit flagged (REWIRE_PLAN §1g). The live v2 pipeline
does NOT use it; the **validated** backtester is `backend/engine/backtest_fast.py`, proven
trade-for-trade by `scripts/run_runtime_parity.py`. This module survives only behind the
`/simulation/*` research surface and the (frozen) AutoOptimize scorer. Repointing it onto
`engine/backtest_fast` is the deferred "strangle" task — large because the SimulationTrade
schema is built around the ladder. Treat its numbers as exploratory, not the v2 edge.

This engine does NOT rely on pre-saved scan_results. Instead, it:
1. Fetches OHLCV for the entire NIFTY universe (~464 stocks) in one batch
2. Pre-computes all PPC detection metrics as vectorized pandas Series
3. For each trading day, checks PPC conditions using pre-computed values
4. Simulates entries, exits, and position management using the same rules

This answers: "If I had been running this system every day from date X to date Y,
what would ₹1,00,000 have become?"
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix
from backend.database import SimulationRun, SimulationTrade, SessionLocal
from backend.intelligence.strategy import PARAMETERS
from backend.services.position_calculator import calculate_position
from backend.services.trading_rules import TRADING_RULES

# Re-export extracted modules so external imports still work
from backend.services.backtest_metrics import compute_total_pnl  # noqa: F401
from backend.services.backtest_strategies import (  # noqa: F401
    precompute_indicators,
    check_stage_fast,
    estimate_base_days_at,
)

logger = logging.getLogger(__name__)

# Need 150 bars before start_date for 150-day SMA (stage analysis) + 50 DMA buffer
HISTORY_BUFFER_DAYS = 350
BATCH_SIZE = 50

# Liquidity filter: ₹1 crore ADT
MIN_ADT = 1_00_00_000

# 50 DMA exit only applies after this many trading days of holding
MIN_HOLD_DAYS_FOR_DMA_EXIT = 10

# Pending entries stay alive for this many trading days before being abandoned
PENDING_ENTRY_MAX_DAYS = 3

# yfinance download timeout per batch (seconds)
YFINANCE_BATCH_TIMEOUT_SECS = 120

# How often to flush progress to DB (every N trading days)
PROGRESS_FLUSH_INTERVAL = 10

# Max backtest runtime before auto-marking as failed (seconds)
MAX_BACKTEST_RUNTIME_SECS = 45 * 60  # 45 minutes

# Stuck detection: if a RUNNING backtest has not updated in this many seconds, treat as stuck
STUCK_THRESHOLD_SECS = 30 * 60  # 30 minutes

# Keep old private names available for internal use
_precompute_indicators = precompute_indicators
_check_stage_fast = check_stage_fast
_estimate_base_days_at = estimate_base_days_at
_compute_total_pnl = compute_total_pnl


def run_backtest(
    db: Session,
    start_date: date,
    end_date: date,
    starting_capital: float,
    rpt_pct: float,
    name: str | None = None,
) -> SimulationRun:
    """
    Create a backtest run record and launch the backtest in a background thread.
    Returns immediately with RUNNING status.
    """
    run = SimulationRun(
        run_type="BACKTEST",
        name=name or f"Backtest {start_date} to {end_date}",
        starting_capital=starting_capital,
        rpt_pct=rpt_pct,
        start_date=start_date,
        end_date=end_date,
        status="RUNNING",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    import threading
    run_id = run.id
    thread = threading.Thread(
        target=_run_backtest_background,
        args=(run_id, start_date, end_date, starting_capital, rpt_pct),
        daemon=True,
    )
    thread.start()

    return run


def _run_backtest_background(
    run_id: int,
    start_date: date,
    end_date: date,
    starting_capital: float,
    rpt_pct: float,
) -> None:
    """Background thread: runs the full backtest with its own DB session."""
    # expire_on_commit=False prevents SQLAlchemy from reloading SimulationTrade
    # objects as Decimal after progress-reporting commits. The backtest loop
    # sets values as float and must keep reading them as float.
    db = SessionLocal(expire_on_commit=False)
    run = None
    try:
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if not run:
            logger.error(f"Backtest run {run_id} not found")
            return

        _execute_backtest(db, run, start_date, end_date, starting_capital, rpt_pct)
        if run.status != "FAILED":
            run.status = "COMPLETED"

    except Exception as exc:
        logger.error(f"Backtest {run_id} failed: {exc}", exc_info=True)
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if run:
            run.status = "FAILED"
            run.error_message = str(exc)[:500]

    finally:
        if run:
            run.updated_at = datetime.now().isoformat()
            db.commit()
        db.close()


def cleanup_stuck_backtests() -> list[int]:
    """Mark any RUNNING backtests that haven't updated recently as FAILED.

    Returns list of run IDs that were cleaned up.
    """
    db = SessionLocal()
    cleaned: list[int] = []
    try:
        running = (
            db.query(SimulationRun)
            .filter(SimulationRun.status == "RUNNING")
            .all()
        )
        now = datetime.now()
        for run in running:
            updated = None
            if run.updated_at:
                try:
                    updated = datetime.fromisoformat(str(run.updated_at))
                except (ValueError, TypeError):
                    pass
            if updated is None and run.created_at:
                try:
                    updated = datetime.fromisoformat(str(run.created_at))
                except (ValueError, TypeError):
                    pass

            if updated is None:
                run.status = "FAILED"
                run.error_message = "Marked as failed: unable to determine last update time"
                run.updated_at = now.isoformat()
                cleaned.append(run.id)
                continue

            elapsed = (now - updated).total_seconds()
            if elapsed > STUCK_THRESHOLD_SECS:
                run.status = "FAILED"
                run.error_message = f"Marked as failed: no update for {int(elapsed // 60)} minutes (likely server restart or hang)"
                run.updated_at = now.isoformat()
                cleaned.append(run.id)

        if cleaned:
            db.commit()
            logger.info(f"Cleaned up {len(cleaned)} stuck backtests: {cleaned}")
    finally:
        db.close()
    return cleaned


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _fetch_universe_ohlcv(start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for the full NIFTY universe in batches."""
    import yfinance as yf

    all_symbols = get_yfinance_symbols()
    result: dict[str, pd.DataFrame] = {}
    total_batches = (len(all_symbols) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        batch = all_symbols[start:start + BATCH_SIZE]
        logger.info(f"Fetching OHLCV batch {batch_idx + 1}/{total_batches} ({len(batch)} symbols)")

        try:
            data = yf.download(
                tickers=batch,
                start=start_date,
                end=end_date,
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
                timeout=YFINANCE_BATCH_TIMEOUT_SECS,
            )

            if data.empty:
                continue

            if len(batch) == 1:
                clean = strip_ns_suffix(batch[0])
                df = data.dropna(subset=["Close"])
                if len(df) >= 30:
                    result[clean] = df
            else:
                for yf_sym in batch:
                    clean = strip_ns_suffix(yf_sym)
                    try:
                        if yf_sym in data.columns.get_level_values(0):
                            df = data[yf_sym].dropna(subset=["Close"])
                            if len(df) >= 30:
                                result[clean] = df
                    except (KeyError, TypeError):
                        pass

        except Exception as exc:
            logger.error(f"Batch {batch_idx + 1} failed: {exc}")

    logger.info(f"Total: {len(result)} stocks with valid data")
    return result


# ---------------------------------------------------------------------------
# Core backtest
# ---------------------------------------------------------------------------

def _execute_backtest(
    db: Session,
    run: SimulationRun,
    start_date: date,
    end_date: date,
    starting_capital: float,
    rpt_pct: float,
) -> None:
    """Core backtest loop with built-in PPC scanning."""

    # Step 1: Fetch OHLCV for full universe
    fetch_start = (start_date - timedelta(days=HISTORY_BUFFER_DAYS)).strftime("%Y-%m-%d")
    fetch_end = (end_date + timedelta(days=5)).strftime("%Y-%m-%d")

    logger.info(f"Backtest {run.id}: fetching OHLCV for full universe ({fetch_start} to {fetch_end})")

    # Report "fetching" phase to frontend
    run.error_message = json.dumps({"phase": "fetching", "progress_pct": 0})
    run.updated_at = datetime.now().isoformat()
    db.commit()

    ohlcv_data = _fetch_universe_ohlcv(fetch_start, fetch_end)

    if not ohlcv_data:
        run.error_message = "Failed to fetch OHLCV data"
        run.status = "FAILED"
        return

    # Step 2: Pre-compute all indicators
    logger.info(f"Backtest {run.id}: pre-computing indicators for {len(ohlcv_data)} stocks")

    run.error_message = json.dumps({"phase": "computing", "progress_pct": 0, "stocks": len(ohlcv_data)})
    run.updated_at = datetime.now().isoformat()
    db.commit()
    indicators = _precompute_indicators(ohlcv_data)

    # Build sorted list of trading days
    all_date_strs: set[str] = set()
    for ind in indicators.values():
        all_date_strs.update(ind["close"].keys())

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    trading_days: list[str] = sorted(ds for ds in all_date_strs if start_str <= ds <= end_str)

    if not trading_days:
        run.error_message = "No trading days found in date range"
        run.status = "FAILED"
        return

    total_days = len(trading_days)
    logger.info(f"Backtest {run.id}: replaying {total_days} trading days across {len(indicators)} stocks")

    # Store phase + total for progress tracking
    run.error_message = json.dumps({
        "phase": "scanning",
        "progress_pct": 0,
        "days_total": total_days,
        "days_done": 0,
    })
    run.updated_at = datetime.now().isoformat()
    db.commit()

    # Map date_str to DataFrame index for base_days computation
    df_date_indices: dict[str, dict[str, int]] = {}
    for symbol, ind in indicators.items():
        df = ind["_df"]
        idx_map: dict[str, int] = {}
        for i, idx in enumerate(df.index):
            ds = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx.date())
            idx_map[ds] = i
        df_date_indices[symbol] = idx_map

    # State
    cash = starting_capital
    open_positions: list[SimulationTrade] = []
    closed_positions: list[SimulationTrade] = []
    pending_entries: list[dict] = []
    equity_curve: list[dict] = []
    peak_equity = starting_capital
    max_drawdown_pct = 0.0
    max_drawdown_amount = 0.0

    pos_meta: dict[int, dict] = {}

    backtest_start_time = time.monotonic()

    # Step 3: Day loop
    for day_idx_loop, day_str in enumerate(trading_days):

        # --- Progress reporting (every N days) ---
        if day_idx_loop % PROGRESS_FLUSH_INTERVAL == 0 or day_idx_loop == total_days - 1:
            progress_pct = round((day_idx_loop / max(total_days, 1)) * 100, 1)
            run.last_processed_date = date.fromisoformat(day_str)
            run.error_message = json.dumps({
                "phase": "scanning",
                "progress_pct": progress_pct,
                "days_total": total_days,
                "days_done": day_idx_loop,
                "current_date": day_str,
                "open_positions": len(open_positions),
            })
            run.updated_at = datetime.now().isoformat()
            db.commit()

        # --- Runtime guard ---
        elapsed = time.monotonic() - backtest_start_time
        if elapsed > MAX_BACKTEST_RUNTIME_SECS:
            run.status = "FAILED"
            run.error_message = f"Backtest timed out after {int(elapsed // 60)} minutes ({day_idx_loop}/{total_days} days processed)"
            return

        # --- Check exits on open positions ---
        still_open: list[SimulationTrade] = []
        for pos in open_positions:
            ind = indicators.get(pos.symbol)
            if not ind:
                still_open.append(pos)
                continue

            day_high = ind["high"].get(day_str)
            day_low = ind["low"].get(day_str)
            day_close = ind["close"].get(day_str)
            if day_high is None or day_low is None or day_close is None:
                still_open.append(pos)
                continue

            remaining = pos.remaining_qty or 0
            if remaining <= 0:
                closed_positions.append(pos)
                continue

            entry_price = float(pos.entry_price or 0)
            total_qty = pos.total_qty or remaining
            trp_value = entry_price * (float(pos.trp_pct or 0) / 100) if pos.trp_pct else 0

            # Init/update position metadata
            meta = pos_meta.get(pos.id, {
                "effective_sl": float(pos.sl_price or 0),
                "hold_days": 0,
                "was_above_dma50": False,
                "consec_below_dma": 0,
                "consec_above_dma20": 0,
                "is_extended": False,
            })
            meta["hold_days"] += 1
            dma50 = ind["dma50"].get(day_str)
            if dma50 and day_close > dma50:
                meta["was_above_dma50"] = True
                meta["consec_below_dma"] = 0
            elif dma50 and day_close < dma50:
                meta["consec_below_dma"] = meta.get("consec_below_dma", 0) + 1
            effective_sl = meta["effective_sl"]
            pos_meta[pos.id] = meta

            # SL check — uses trailed (effective) SL, not original
            if effective_sl > 0 and day_low <= effective_sl:
                exit_price = effective_sl
                sl_pnl = (exit_price - entry_price) * remaining
                cash += exit_price * remaining
                pos.qty_exited_sl = remaining
                pos.remaining_qty = 0
                pos.status = "CLOSED"
                pos.exit_date = date.fromisoformat(day_str)
                prior_pnl = _compute_total_pnl(pos, entry_price, sl_exit_price=exit_price)
                pos.gross_pnl = round(prior_pnl, 2)
                if trp_value > 0 and total_qty > 0:
                    pos.r_multiple = round(prior_pnl / (trp_value * total_qty), 2)
                pos.pnl_pct = round((prior_pnl / (entry_price * total_qty)) * 100, 2) if (entry_price * total_qty) > 0 else 0
                closed_positions.append(pos)
                continue

            # Target checks
            exited_this_day = 0

            t_2r = float(pos.target_2r or 0)
            t_ne = float(pos.target_ne or 0)
            t_ge = float(pos.target_ge or 0)
            t_ee = float(pos.target_ee or 0)

            if t_2r and day_high >= t_2r and (pos.qty_exited_2r or 0) == 0:
                exit_qty = min(max(1, round(total_qty * TRADING_RULES["mathematical_exit_pct"])), remaining)
                if exit_qty > 0:
                    cash += t_2r * exit_qty
                    pos.qty_exited_2r = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty
                    meta["effective_sl"] = entry_price

            if remaining > 0 and t_ne and day_high >= t_ne and (pos.qty_exited_ne or 0) == 0:
                exit_qty = min(max(1, round(remaining * TRADING_RULES["ne_exit_pct"])), remaining)
                if exit_qty > 0:
                    cash += t_ne * exit_qty
                    pos.qty_exited_ne = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty
                    meta["effective_sl"] = t_2r

            if remaining > 0 and t_ge and day_high >= t_ge and (pos.qty_exited_ge or 0) == 0:
                exit_qty = min(max(1, round(remaining * TRADING_RULES["ge_exit_pct"])), remaining)
                if exit_qty > 0:
                    cash += t_ge * exit_qty
                    pos.qty_exited_ge = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty
                    meta["effective_sl"] = t_ne
                    meta["is_extended"] = True

            if remaining > 0 and t_ee and day_high >= t_ee and (pos.qty_exited_ee or 0) == 0:
                exit_qty = min(max(1, round(remaining * TRADING_RULES["ee_exit_pct"])), remaining)
                if exit_qty > 0:
                    cash += t_ee * exit_qty
                    pos.qty_exited_ee = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty
                    meta["effective_sl"] = t_ge

            # LOD trailing
            if remaining > 0 and meta.get("is_extended"):
                meta["effective_sl"] = max(meta["effective_sl"], day_low)

            # 50 DMA / 20 DMA final exit
            dma20 = ind["dma20"].get(day_str)
            if dma20 and day_close > dma20:
                meta["consec_above_dma20"] = meta.get("consec_above_dma20", 0) + 1
            else:
                meta["consec_above_dma20"] = 0

            use_dma20 = meta.get("consec_above_dma20", 0) >= 60
            final_dma = dma20 if (use_dma20 and dma20) else dma50

            if (
                remaining > 0
                and meta["hold_days"] >= MIN_HOLD_DAYS_FOR_DMA_EXIT
                and meta["was_above_dma50"]
                and final_dma
                and day_close < final_dma
            ):
                exit_price_final = day_close
                cash += exit_price_final * remaining
                pos.qty_exited_final = remaining
                remaining = 0

            pos.remaining_qty = remaining
            if remaining <= 0:
                pos.status = "CLOSED"
                pos.exit_date = date.fromisoformat(day_str)
                total_pnl = _compute_total_pnl(pos, entry_price)
                if pos.qty_exited_final and pos.qty_exited_final > 0:
                    final_exit_price = day_close
                    total_pnl += (final_exit_price - entry_price) * pos.qty_exited_final
                pos.gross_pnl = round(total_pnl, 2)
                if trp_value > 0 and total_qty > 0:
                    pos.r_multiple = round(total_pnl / (trp_value * total_qty), 2)
                pos.pnl_pct = round((total_pnl / (entry_price * total_qty)) * 100, 2) if (entry_price * total_qty) > 0 else 0
                closed_positions.append(pos)
            else:
                if exited_this_day > 0:
                    pos.status = "PARTIAL"
                still_open.append(pos)

        open_positions = still_open

        # --- Process pending entries ---
        new_pending: list[dict] = []
        for entry in pending_entries:
            symbol = entry["symbol"]
            trigger = entry["trigger_level"]
            ind = indicators.get(symbol)
            if not ind:
                continue

            day_high = ind["high"].get(day_str)
            if day_high is None or day_high < trigger:
                entry["days_waiting"] = entry.get("days_waiting", 0) + 1
                if entry["days_waiting"] < PENDING_ENTRY_MAX_DAYS:
                    new_pending.append(entry)
                continue

            equity = cash + sum(
                (p.remaining_qty or 0) * float(indicators.get(p.symbol, {}).get("close", {}).get(day_str, p.entry_price or 0))
                for p in open_positions
            )

            current_risk = sum(float(p.rpt_amount or 0) for p in open_positions)
            max_risk = equity * (TRADING_RULES["max_open_risk_pct"] / 100)

            trp_pct = entry["trp_pct"]
            sizing = calculate_position(equity, rpt_pct, trigger, trp_pct)

            # Convert Decimal sizing values to float for backtest arithmetic
            sz_sl = float(sizing["sl_price"])
            sz_rpt = float(sizing["rpt_amount"])
            sz_2r = float(sizing["target_2r"])
            sz_ne = float(sizing["target_ne"])
            sz_ge = float(sizing["target_ge"])
            sz_ee = float(sizing["target_ee"])

            if sizing["position_size"] < 2:
                continue
            if current_risk + sz_rpt > max_risk:
                continue
            if trigger * sizing["position_size"] > cash:
                continue

            sim_trade = SimulationTrade(
                run_id=run.id,
                symbol=symbol,
                signal_date=date.fromisoformat(entry["signal_date"]),
                entry_date=date.fromisoformat(day_str),
                entry_price=trigger,
                total_qty=sizing["position_size"],
                half_qty=sizing["half_qty"],
                trp_pct=trp_pct,
                sl_price=sz_sl,
                rpt_amount=sz_rpt,
                target_2r=sz_2r,
                target_ne=sz_ne,
                target_ge=sz_ge,
                target_ee=sz_ee,
                remaining_qty=sizing["position_size"],
                status="OPEN",
                portfolio_value_at_entry=equity,
            )
            db.add(sim_trade)
            db.flush()
            cash -= trigger * sizing["position_size"]
            open_positions.append(sim_trade)

        pending_entries = new_pending

        # --- Run PPC scan on today's candles ---
        open_symbols = {p.symbol for p in open_positions}
        pending_symbols = {e["symbol"] for e in pending_entries}

        for symbol, ind in indicators.items():
            if symbol in open_symbols or symbol in pending_symbols:
                continue

            trp_ratio_val = ind["trp_ratio"].get(day_str)
            close_pos_val = ind["close_pos"].get(day_str)
            vol_ratio_val = ind["vol_ratio"].get(day_str)
            is_green_val = ind["is_green"].get(day_str)
            adt_val = ind["adt"].get(day_str)

            if (
                trp_ratio_val is None
                or close_pos_val is None
                or vol_ratio_val is None
                or is_green_val is None
                or adt_val is None
            ):
                continue

            if not (
                trp_ratio_val >= PARAMETERS.get("ppc_trp_ratio_min", 1.5)
                and close_pos_val >= PARAMETERS.get("ppc_close_position_min", 0.60)
                and vol_ratio_val >= PARAMETERS.get("ppc_volume_ratio_min", 1.5)
                and is_green_val
                and adt_val >= MIN_ADT
            ):
                continue

            stage = _check_stage_fast(ind, day_str)
            if stage not in ("S1B", "S2"):
                continue

            df = ind["_df"]
            day_idx_map = df_date_indices.get(symbol, {})
            day_idx = day_idx_map.get(day_str)
            if day_idx is None:
                continue

            base_days, base_quality = _estimate_base_days_at(df, day_idx)
            min_base = max(
                TRADING_RULES["min_base_bars"],
                int(PARAMETERS.get("min_base_days", 20)),
            )
            if base_days < min_base:
                continue

            trp_pct = ind["trp_pct"].get(day_str, 0)
            if trp_pct < TRADING_RULES["min_trp"]:
                continue

            trigger_level = ind["high"].get(day_str)
            if trigger_level is None:
                continue

            pending_entries.append({
                "symbol": symbol,
                "trigger_level": round(trigger_level, 2),
                "signal_date": day_str,
                "trp_pct": round(trp_pct, 2),
                "days_waiting": 0,
            })

        # --- Record equity ---
        mtm = sum(
            (p.remaining_qty or 0) * float(indicators.get(p.symbol, {}).get("close", {}).get(day_str, p.entry_price or 0))
            for p in open_positions
        )
        equity = cash + mtm
        equity_curve.append({"date": day_str, "equity": round(equity, 2)})

        if equity > peak_equity:
            peak_equity = equity
        if peak_equity > 0:
            dd_pct = ((peak_equity - equity) / peak_equity) * 100
            dd_amount = peak_equity - equity
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct
                max_drawdown_amount = dd_amount

    # --- Close remaining positions at last day's close ---
    last_day = trading_days[-1] if trading_days else end_date.isoformat()
    for pos in open_positions:
        ind = indicators.get(pos.symbol, {})
        close_price = float(ind.get("close", {}).get(last_day, pos.entry_price or 0))
        remaining = pos.remaining_qty or 0
        if remaining > 0:
            entry_price = float(pos.entry_price or 0)
            cash += close_price * remaining
            pos.qty_exited_final = remaining
            pos.remaining_qty = 0
            pos.status = "CLOSED"
            pos.exit_date = date.fromisoformat(last_day)
            total_pnl = _compute_total_pnl(pos, entry_price)
            total_pnl += (close_price - entry_price) * remaining
            pos.gross_pnl = round(total_pnl, 2)
            trp_pct_val = float(pos.trp_pct or 0)
            trp_value = entry_price * (trp_pct_val / 100) if trp_pct_val else 0
            total_qty = pos.total_qty or 1
            if trp_value > 0 and total_qty > 0:
                pos.r_multiple = round(total_pnl / (trp_value * total_qty), 2)
            pos.pnl_pct = round((total_pnl / (entry_price * total_qty)) * 100, 2) if (entry_price * total_qty) > 0 else 0
        closed_positions.append(pos)

    # --- Compute summary stats ---
    all_trades = closed_positions
    wins = [t for t in all_trades if t.gross_pnl and t.gross_pnl > 0]
    losses = [t for t in all_trades if t.gross_pnl is not None and t.gross_pnl <= 0]

    final_equity = cash
    total_pnl = final_equity - starting_capital
    total_return_pct = (total_pnl / starting_capital) * 100 if starting_capital > 0 else 0
    win_rate = (len(wins) / len(all_trades) * 100) if all_trades else None

    avg_win_r = None
    avg_loss_r = None
    if wins:
        win_rs = [t.r_multiple for t in wins if t.r_multiple is not None]
        if win_rs:
            avg_win_r = round(sum(win_rs) / len(win_rs), 2)
    if losses:
        loss_rs = [abs(t.r_multiple) for t in losses if t.r_multiple is not None]
        if loss_rs:
            avg_loss_r = round(sum(loss_rs) / len(loss_rs), 2)

    arr_val = round(avg_win_r / avg_loss_r, 2) if avg_win_r and avg_loss_r and avg_loss_r > 0 else None

    expectancy = None
    if win_rate is not None and avg_win_r is not None and avg_loss_r is not None:
        win_pct = win_rate / 100
        loss_pct = 1 - win_pct
        expectancy = round((win_pct * avg_win_r) - (loss_pct * avg_loss_r), 2)

    run.final_capital = round(final_equity, 2)
    run.total_pnl = round(total_pnl, 2)
    run.total_return_pct = round(total_return_pct, 2)
    run.total_trades = len(all_trades)
    run.win_count = len(wins)
    run.loss_count = len(losses)
    run.win_rate = round(win_rate, 2) if win_rate is not None else None
    run.avg_win_r = avg_win_r
    run.avg_loss_r = avg_loss_r
    run.arr = arr_val
    run.expectancy = expectancy
    run.max_drawdown_pct = round(max_drawdown_pct, 2)
    run.max_drawdown_amount = round(max_drawdown_amount, 2)
    run.equity_curve = json.dumps(equity_curve)

    # Clear progress data from error_message (only used during running)
    run.error_message = None

    db.commit()
    logger.info(
        f"Backtest {run.id} completed: {len(all_trades)} trades, "
        f"{total_return_pct:.2f}% return, {len(trading_days)} days replayed"
    )
