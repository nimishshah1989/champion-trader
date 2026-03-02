"""
Backtest engine — replays historical scan_results against OHLCV data
to simulate what the Champion Trader methodology would have produced.

Algorithm (day-by-day replay):
1. Setup: Load scan_results for date range. Pre-fetch ALL OHLCV in one batch.
2. Day loop:
   - Check exits on open positions (SL via Low, targets via High, 50 DMA via Close)
   - Process pending entries from previous day's signals
   - Collect new signals from today's scan_results
   - Record equity: cash + mark-to-market of open positions
3. Compute stats: Win rate, ARR, expectancy, max drawdown. Persist results.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from backend.database import ScanResult, SimulationRun, SimulationTrade, SessionLocal
from backend.services.position_calculator import calculate_position
from backend.services.trading_rules import TRADING_RULES

logger = logging.getLogger(__name__)

# Buffer before start_date so we have enough history for 50 DMA
DMA_BUFFER_DAYS = 300


def _fetch_ohlcv_batch(symbols: list[str], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
    """Pre-fetch OHLCV data for a batch of symbols in one yfinance call."""
    import yfinance as yf

    if not symbols:
        return {}

    yf_symbols = [f"{s}.NS" for s in symbols]
    result: dict[str, pd.DataFrame] = {}

    try:
        data = yf.download(
            tickers=yf_symbols,
            start=start_date,
            end=end_date,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )

        if data.empty:
            return {}

        if len(yf_symbols) == 1:
            clean = yf_symbols[0].replace(".NS", "")
            df = data.dropna(subset=["Close"])
            if len(df) >= 5:
                result[clean] = df
        else:
            for yf_sym in yf_symbols:
                clean = yf_sym.replace(".NS", "")
                try:
                    if yf_sym in data.columns.get_level_values(0):
                        df = data[yf_sym].dropna(subset=["Close"])
                        if len(df) >= 5:
                            result[clean] = df
                except (KeyError, TypeError):
                    pass

    except Exception as exc:
        logger.error(f"Backtest OHLCV fetch failed: {exc}")

    return result


def _preprocess_ohlcv(ohlcv_data: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """
    Pre-process OHLCV data for fast day-by-day lookups.
    Returns {symbol: {"daily": {date_str: {o,h,l,c}}, "dma50": {date_str: float}}}
    This avoids repeated DataFrame indexing during the backtest loop.
    """
    processed: dict[str, dict] = {}

    for symbol, df in ohlcv_data.items():
        # Pre-compute 50 DMA as a rolling column
        dma50_series = df["Close"].rolling(window=50, min_periods=50).mean()

        daily: dict[str, dict] = {}
        dma50: dict[str, float] = {}

        for idx in df.index:
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx.date())
            daily[date_str] = {
                "open": float(df.loc[idx, "Open"]),
                "high": float(df.loc[idx, "High"]),
                "low": float(df.loc[idx, "Low"]),
                "close": float(df.loc[idx, "Close"]),
            }
            dma_val = dma50_series.loc[idx]
            if pd.notna(dma_val):
                dma50[date_str] = float(dma_val)

        processed[symbol] = {"daily": daily, "dma50": dma50}

    return processed


def run_backtest(
    db: Session,
    start_date: date,
    end_date: date,
    starting_capital: float,
    rpt_pct: float,
    name: str | None = None,
) -> SimulationRun:
    """
    Create a backtest run record and return it immediately.
    The actual backtest runs in a background thread.
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

    # Launch backtest in background thread with its own DB session
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
    db = SessionLocal()
    try:
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if not run:
            logger.error(f"Backtest run {run_id} not found")
            return

        _execute_backtest(db, run, start_date, end_date, starting_capital, rpt_pct)
        # Only mark COMPLETED if _execute_backtest didn't already set FAILED
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


def _execute_backtest(
    db: Session,
    run: SimulationRun,
    start_date: date,
    end_date: date,
    starting_capital: float,
    rpt_pct: float,
) -> None:
    """Core backtest loop."""

    # Step 1: Load scan_results for date range
    scans = (
        db.query(ScanResult)
        .filter(
            ScanResult.scan_date >= start_date,
            ScanResult.scan_date <= end_date,
            ScanResult.scan_type == "PPC",
        )
        .order_by(ScanResult.scan_date)
        .all()
    )

    if not scans:
        run.error_message = "No PPC scan results found in date range"
        run.status = "FAILED"
        return

    # Collect unique symbols from scans
    all_symbols = list({s.symbol for s in scans})
    logger.info(f"Backtest {run.id}: {len(scans)} signals across {len(all_symbols)} symbols, {start_date} to {end_date}")

    # Step 2: Pre-fetch ALL OHLCV data with DMA buffer
    fetch_start = (start_date - timedelta(days=DMA_BUFFER_DAYS)).strftime("%Y-%m-%d")
    fetch_end = (end_date + timedelta(days=5)).strftime("%Y-%m-%d")

    ohlcv_data: dict[str, pd.DataFrame] = {}
    batch_size = 50
    for i in range(0, len(all_symbols), batch_size):
        batch = all_symbols[i:i + batch_size]
        logger.info(f"Backtest {run.id}: fetching OHLCV batch {i // batch_size + 1} ({len(batch)} symbols)")
        batch_data = _fetch_ohlcv_batch(batch, fetch_start, fetch_end)
        ohlcv_data.update(batch_data)

    logger.info(f"Backtest {run.id}: fetched OHLCV for {len(ohlcv_data)}/{len(all_symbols)} symbols")

    # Pre-process into fast lookup dicts
    lookup = _preprocess_ohlcv(ohlcv_data)

    # Group scan results by date
    scans_by_date: dict[date, list[ScanResult]] = {}
    for scan in scans:
        scans_by_date.setdefault(scan.scan_date, []).append(scan)

    # Build sorted list of trading days from the pre-processed data
    all_date_strs: set[str] = set()
    for sym_data in lookup.values():
        all_date_strs.update(sym_data["daily"].keys())

    trading_days: list[date] = []
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    for ds in sorted(all_date_strs):
        if start_str <= ds <= end_str:
            trading_days.append(date.fromisoformat(ds))

    if not trading_days:
        run.error_message = "No trading days found in OHLCV data"
        run.status = "FAILED"
        return

    logger.info(f"Backtest {run.id}: {len(trading_days)} trading days to replay")

    # State
    cash = starting_capital
    open_positions: list[SimulationTrade] = []
    closed_positions: list[SimulationTrade] = []
    pending_entries: list[dict] = []
    equity_curve: list[dict] = []
    peak_equity = starting_capital
    max_drawdown_pct = 0.0
    max_drawdown_amount = 0.0

    # Step 3: Day loop
    for day in trading_days:
        day_str = day.isoformat()

        # --- Check exits on open positions ---
        still_open: list[SimulationTrade] = []
        for pos in open_positions:
            sym_lookup = lookup.get(pos.symbol)
            if not sym_lookup:
                still_open.append(pos)
                continue

            day_data = sym_lookup["daily"].get(day_str)
            if day_data is None:
                still_open.append(pos)
                continue

            remaining = pos.remaining_qty or 0
            if remaining <= 0:
                closed_positions.append(pos)
                continue

            entry_price = pos.entry_price or 0
            total_qty = pos.total_qty or remaining
            trp_value = entry_price * (pos.trp_pct / 100) if pos.trp_pct else 0

            # SL check: Low <= sl_price -> exit ALL at sl_price
            if pos.sl_price and day_data["low"] <= pos.sl_price:
                exit_price = pos.sl_price
                pnl = (exit_price - entry_price) * remaining
                cash += exit_price * remaining

                pos.qty_exited_sl = remaining
                pos.remaining_qty = 0
                pos.status = "CLOSED"
                pos.exit_date = day
                pos.gross_pnl = round(pnl, 2)
                if trp_value > 0:
                    pos.r_multiple = round((exit_price - entry_price) / trp_value, 2)
                pos.pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0
                closed_positions.append(pos)
                continue

            # Target checks from lowest up
            exited_this_day = 0

            # 2R
            if pos.target_2r and day_data["high"] >= pos.target_2r and (pos.qty_exited_2r or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["mathematical_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_2r * exit_qty
                    pos.qty_exited_2r = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            # NE
            if pos.target_ne and day_data["high"] >= pos.target_ne and (pos.qty_exited_ne or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["ne_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_ne * exit_qty
                    pos.qty_exited_ne = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            # GE
            if pos.target_ge and day_data["high"] >= pos.target_ge and (pos.qty_exited_ge or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["ge_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_ge * exit_qty
                    pos.qty_exited_ge = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            # EE
            if pos.target_ee and day_data["high"] >= pos.target_ee and (pos.qty_exited_ee or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["ee_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_ee * exit_qty
                    pos.qty_exited_ee = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            # 50 DMA final exit: Close < 50 DMA -> exit remaining
            if remaining > 0:
                dma_50 = sym_lookup["dma50"].get(day_str)
                if dma_50 and day_data["close"] < dma_50:
                    exit_price = day_data["close"]
                    cash += exit_price * remaining
                    pos.qty_exited_final = remaining
                    remaining = 0

            pos.remaining_qty = remaining
            if remaining <= 0:
                pos.status = "CLOSED"
                pos.exit_date = day
                total_pnl = _compute_total_pnl(pos, entry_price)
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

        # --- Process pending entries (signals from yesterday) ---
        for entry in pending_entries:
            symbol = entry["symbol"]
            trigger = entry["trigger_level"]

            sym_lookup = lookup.get(symbol)
            if not sym_lookup:
                continue

            day_data = sym_lookup["daily"].get(day_str)
            if day_data is None:
                continue

            # Enter at trigger_level if day's High >= trigger_level
            if day_data["high"] >= trigger:
                # Current equity for risk check
                equity = cash + sum(
                    (p.remaining_qty or 0) * (lookup.get(p.symbol, {}).get("daily", {}).get(day_str, {}).get("close", p.entry_price or 0))
                    for p in open_positions
                )

                # Max open risk check
                current_risk = sum((p.rpt_amount or 0) for p in open_positions)
                max_risk = equity * (TRADING_RULES["max_open_risk_pct"] / 100)

                trp_pct = entry.get("trp_pct", 3.0)
                sizing = calculate_position(equity, rpt_pct, trigger, trp_pct)

                if current_risk + sizing["rpt_amount"] > max_risk:
                    continue
                position_cost = trigger * sizing["position_size"]
                if position_cost > cash:
                    continue

                sim_trade = SimulationTrade(
                    run_id=run.id,
                    symbol=symbol,
                    signal_date=entry["signal_date"],
                    entry_date=day,
                    entry_price=trigger,
                    total_qty=sizing["position_size"],
                    half_qty=sizing["half_qty"],
                    trp_pct=trp_pct,
                    sl_price=sizing["sl_price"],
                    rpt_amount=sizing["rpt_amount"],
                    target_2r=sizing["target_2r"],
                    target_ne=sizing["target_ne"],
                    target_ge=sizing["target_ge"],
                    target_ee=sizing["target_ee"],
                    remaining_qty=sizing["position_size"],
                    status="OPEN",
                    portfolio_value_at_entry=equity,
                )
                db.add(sim_trade)
                db.flush()
                cash -= position_cost
                open_positions.append(sim_trade)

        # Clear pending — they were all processed or skipped
        pending_entries = []

        # --- Collect new signals for today -> queue as pending for tomorrow ---
        today_scans = scans_by_date.get(day, [])
        for scan in today_scans:
            if scan.trp is None or scan.trp < TRADING_RULES["min_trp"]:
                continue
            if scan.base_days is not None and scan.base_days < TRADING_RULES["min_base_bars"]:
                continue
            if scan.stage and scan.stage not in ("S1B", "S2"):
                continue
            if scan.trigger_level is None:
                continue
            if any(p.symbol == scan.symbol for p in open_positions):
                continue

            pending_entries.append({
                "symbol": scan.symbol,
                "trigger_level": scan.trigger_level,
                "signal_date": day,
                "trp_pct": scan.trp,
            })

        # --- Record equity: cash + mark-to-market ---
        mtm = sum(
            (p.remaining_qty or 0) * lookup.get(p.symbol, {}).get("daily", {}).get(day_str, {}).get("close", p.entry_price or 0)
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

    # --- Close remaining open positions at last day's close ---
    last_day_str = trading_days[-1].isoformat() if trading_days else end_date.isoformat()
    for pos in open_positions:
        sym_lookup = lookup.get(pos.symbol, {})
        close_price = sym_lookup.get("daily", {}).get(last_day_str, {}).get("close", pos.entry_price or 0)
        remaining = pos.remaining_qty or 0
        if remaining > 0:
            entry_price = pos.entry_price or 0
            cash += close_price * remaining
            pos.qty_exited_final = remaining
            pos.remaining_qty = 0
            pos.status = "CLOSED"
            pos.exit_date = trading_days[-1] if trading_days else end_date
            total_pnl = _compute_total_pnl(pos, entry_price)
            # Add the final exit P&L
            total_pnl += (close_price - entry_price) * remaining
            pos.gross_pnl = round(total_pnl, 2)
            trp_value = entry_price * (pos.trp_pct / 100) if pos.trp_pct else 0
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

    db.commit()
    logger.info(f"Backtest {run.id} completed: {len(all_trades)} trades, {total_return_pct:.2f}% return")


def _compute_total_pnl(pos: SimulationTrade, entry_price: float) -> float:
    """Compute total P&L from all partial exits (excluding final exit)."""
    total = 0.0
    if pos.qty_exited_2r and pos.target_2r:
        total += (pos.target_2r - entry_price) * pos.qty_exited_2r
    if pos.qty_exited_ne and pos.target_ne:
        total += (pos.target_ne - entry_price) * pos.qty_exited_ne
    if pos.qty_exited_ge and pos.target_ge:
        total += (pos.target_ge - entry_price) * pos.qty_exited_ge
    if pos.qty_exited_ee and pos.target_ee:
        total += (pos.target_ee - entry_price) * pos.qty_exited_ee
    if pos.qty_exited_sl and pos.sl_price:
        total += (pos.sl_price - entry_price) * pos.qty_exited_sl
    return total
