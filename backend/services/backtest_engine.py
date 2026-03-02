"""
Backtest engine — simulates the full Champion Trader system over a historical period.

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
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix
from backend.database import SimulationRun, SimulationTrade, SessionLocal
from backend.services.position_calculator import calculate_position
from backend.services.trading_rules import TRADING_RULES

logger = logging.getLogger(__name__)

# Need 150 bars before start_date for 150-day SMA (stage analysis) + 50 DMA buffer
HISTORY_BUFFER_DAYS = 350
BATCH_SIZE = 50

# Liquidity filter: ₹1 crore ADT
MIN_ADT = 1_00_00_000


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
    db = SessionLocal()
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
# Pre-compute technical indicators
# ---------------------------------------------------------------------------

def _precompute_indicators(ohlcv: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """
    Pre-compute all PPC detection metrics as vectorized Series.
    Returns {symbol: {trp_ratio, close_pos, vol_ratio, is_green, adt, high, ...}}
    where each value is a dict keyed by date_str for O(1) lookups.
    """
    indicators: dict[str, dict] = {}

    for symbol, df in ohlcv.items():
        try:
            if len(df) < 30:
                continue

            # TRP and ratios
            trp = (df["High"] - df["Low"]) / df["Close"] * 100
            avg_trp = trp.rolling(window=20, min_periods=20).mean()
            trp_ratio = trp / avg_trp.replace(0, np.nan)

            # Close position
            candle_range = df["High"] - df["Low"]
            close_pos = (df["Close"] - df["Low"]) / candle_range.replace(0, np.nan)

            # Volume ratio
            avg_vol = df["Volume"].rolling(window=20, min_periods=20).mean()
            vol_ratio = df["Volume"] / avg_vol.replace(0, np.nan)

            # ADT (rolling)
            turnover = df["Volume"] * df["Close"]
            adt = turnover.rolling(window=20, min_periods=20).mean()

            # Is green candle
            is_green = df["Close"] > df["Open"]

            # 50 DMA for exit signals
            dma50 = df["Close"].rolling(window=50, min_periods=50).mean()

            # 150 DMA for stage analysis (pre-compute for efficiency)
            sma150 = df["Close"].rolling(window=150, min_periods=150).mean()

            # Build date-keyed lookups
            sym_data: dict = {
                "trp_ratio": {},
                "trp_pct": {},
                "close_pos": {},
                "vol_ratio": {},
                "is_green": {},
                "adt": {},
                "high": {},
                "low": {},
                "close": {},
                "open": {},
                "dma50": {},
                "sma150": {},
                "sma150_20ago": {},
            }

            dates = df.index
            for i, idx in enumerate(dates):
                ds = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx.date())

                if pd.notna(trp_ratio.iloc[i]):
                    sym_data["trp_ratio"][ds] = float(trp_ratio.iloc[i])
                if pd.notna(trp.iloc[i]):
                    sym_data["trp_pct"][ds] = float(trp.iloc[i])
                if pd.notna(close_pos.iloc[i]):
                    sym_data["close_pos"][ds] = float(close_pos.iloc[i])
                if pd.notna(vol_ratio.iloc[i]):
                    sym_data["vol_ratio"][ds] = float(vol_ratio.iloc[i])
                sym_data["is_green"][ds] = bool(is_green.iloc[i])
                if pd.notna(adt.iloc[i]):
                    sym_data["adt"][ds] = float(adt.iloc[i])
                sym_data["high"][ds] = float(df["High"].iloc[i])
                sym_data["low"][ds] = float(df["Low"].iloc[i])
                sym_data["close"][ds] = float(df["Close"].iloc[i])
                sym_data["open"][ds] = float(df["Open"].iloc[i])
                if pd.notna(dma50.iloc[i]):
                    sym_data["dma50"][ds] = float(dma50.iloc[i])
                if pd.notna(sma150.iloc[i]):
                    sym_data["sma150"][ds] = float(sma150.iloc[i])
                if i >= 20 and pd.notna(sma150.iloc[i - 20]):
                    sym_data["sma150_20ago"][ds] = float(sma150.iloc[i - 20])

            # Store raw DataFrame for stage/base analysis on PPC candidates
            sym_data["_df"] = df

            indicators[symbol] = sym_data

        except Exception as exc:
            logger.warning(f"Pre-compute failed for {symbol}: {exc}")

    return indicators


def _check_stage_fast(ind: dict, day_str: str) -> str:
    """Fast stage determination using pre-computed SMA values."""
    current_close = ind["close"].get(day_str)
    current_sma = ind["sma150"].get(day_str)
    sma_20_ago = ind["sma150_20ago"].get(day_str)

    if current_close is None or current_sma is None or sma_20_ago is None:
        return "UNKNOWN"

    sma_slope_pct = (current_sma - sma_20_ago) / sma_20_ago * 100
    price_vs_sma_pct = (current_close - current_sma) / current_sma * 100

    if price_vs_sma_pct < -5 and sma_slope_pct < -0.5:
        return "S4"
    if price_vs_sma_pct > 3 and sma_slope_pct > 0.5:
        return "S2"
    if -3 <= price_vs_sma_pct <= 8 and -0.5 <= sma_slope_pct <= 1.5:
        if price_vs_sma_pct > 0:
            return "S1B"
        return "S1"
    if -5 <= price_vs_sma_pct <= 3 and -1.0 <= sma_slope_pct <= 0.5:
        return "S3"
    if -5 <= price_vs_sma_pct <= 5 and abs(sma_slope_pct) < 1.0:
        return "S1"
    if price_vs_sma_pct > 0:
        return "S2"
    return "S4"


def _estimate_base_days_at(df: pd.DataFrame, day_idx: int) -> tuple[int, str]:
    """Estimate base days at a specific index in the DataFrame."""
    if day_idx < 30:
        return (0, "UNKNOWN")

    closes = df["Close"].values[:day_idx + 1]
    highs = df["High"].values[:day_idx + 1]

    lookback = min(60, len(highs))
    recent_high = float(np.max(highs[-lookback:]))
    upper_bound = recent_high * 1.02
    lower_bound = recent_high * 0.85

    base_days = 0
    for i in range(len(closes) - 1, -1, -1):
        if lower_bound <= closes[i] <= upper_bound:
            base_days += 1
        else:
            break

    if base_days < 10:
        return (base_days, "UNKNOWN")

    base_slice_h = df["High"].values[day_idx - base_days + 1:day_idx + 1]
    base_slice_l = df["Low"].values[day_idx - base_days + 1:day_idx + 1]
    base_slice_c = df["Close"].values[day_idx - base_days + 1:day_idx + 1]

    if len(base_slice_c) == 0:
        return (base_days, "UNKNOWN")

    daily_ranges = (base_slice_h - base_slice_l) / np.where(base_slice_c == 0, 1, base_slice_c)
    range_std = float(np.std(daily_ranges))

    if range_std < 0.015:
        quality = "SMOOTH"
    elif range_std < 0.025:
        quality = "MIXED"
    else:
        quality = "CHOPPY"

    return (base_days, quality)


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
    ohlcv_data = _fetch_universe_ohlcv(fetch_start, fetch_end)

    if not ohlcv_data:
        run.error_message = "Failed to fetch OHLCV data"
        run.status = "FAILED"
        return

    # Step 2: Pre-compute all indicators
    logger.info(f"Backtest {run.id}: pre-computing indicators for {len(ohlcv_data)} stocks")
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

    logger.info(f"Backtest {run.id}: replaying {len(trading_days)} trading days across {len(indicators)} stocks")

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

    # Step 3: Day loop
    for day_str in trading_days:

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

            entry_price = pos.entry_price or 0
            total_qty = pos.total_qty or remaining
            trp_value = entry_price * (pos.trp_pct / 100) if pos.trp_pct else 0

            # SL check
            if pos.sl_price and day_low <= pos.sl_price:
                exit_price = pos.sl_price
                pnl = (exit_price - entry_price) * remaining
                cash += exit_price * remaining
                pos.qty_exited_sl = remaining
                pos.remaining_qty = 0
                pos.status = "CLOSED"
                pos.exit_date = date.fromisoformat(day_str)
                pos.gross_pnl = round(pnl, 2)
                if trp_value > 0:
                    pos.r_multiple = round((exit_price - entry_price) / trp_value, 2)
                pos.pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0
                closed_positions.append(pos)
                continue

            # Target checks
            exited_this_day = 0

            if pos.target_2r and day_high >= pos.target_2r and (pos.qty_exited_2r or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["mathematical_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_2r * exit_qty
                    pos.qty_exited_2r = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            if pos.target_ne and day_high >= pos.target_ne and (pos.qty_exited_ne or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["ne_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_ne * exit_qty
                    pos.qty_exited_ne = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            if pos.target_ge and day_high >= pos.target_ge and (pos.qty_exited_ge or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["ge_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_ge * exit_qty
                    pos.qty_exited_ge = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            if pos.target_ee and day_high >= pos.target_ee and (pos.qty_exited_ee or 0) == 0:
                exit_qty = min(int(total_qty * TRADING_RULES["ee_exit_pct"]), remaining)
                if exit_qty > 0:
                    cash += pos.target_ee * exit_qty
                    pos.qty_exited_ee = exit_qty
                    remaining -= exit_qty
                    exited_this_day += exit_qty

            # 50 DMA final exit
            if remaining > 0:
                dma50 = ind["dma50"].get(day_str)
                if dma50 and day_close < dma50:
                    cash += day_close * remaining
                    pos.qty_exited_final = remaining
                    remaining = 0

            pos.remaining_qty = remaining
            if remaining <= 0:
                pos.status = "CLOSED"
                pos.exit_date = date.fromisoformat(day_str)
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
            ind = indicators.get(symbol)
            if not ind:
                continue

            day_high = ind["high"].get(day_str)
            if day_high is None or day_high < trigger:
                continue

            # Calculate current equity
            equity = cash + sum(
                (p.remaining_qty or 0) * (indicators.get(p.symbol, {}).get("close", {}).get(day_str, p.entry_price or 0))
                for p in open_positions
            )

            # Max open risk check
            current_risk = sum((p.rpt_amount or 0) for p in open_positions)
            max_risk = equity * (TRADING_RULES["max_open_risk_pct"] / 100)

            trp_pct = entry["trp_pct"]
            sizing = calculate_position(equity, rpt_pct, trigger, trp_pct)

            if current_risk + sizing["rpt_amount"] > max_risk:
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
            cash -= trigger * sizing["position_size"]
            open_positions.append(sim_trade)

        pending_entries = []

        # --- Run PPC scan on today's candles across the full universe ---
        open_symbols = {p.symbol for p in open_positions}

        for symbol, ind in indicators.items():
            if symbol in open_symbols:
                continue

            # Fast PPC check using pre-computed values
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

            # PPC conditions
            if not (
                trp_ratio_val >= 1.5
                and close_pos_val >= 0.60
                and vol_ratio_val >= 1.5
                and is_green_val
                and adt_val >= MIN_ADT
            ):
                continue

            # PPC candidate — now check stage and base (only for matches)
            stage = _check_stage_fast(ind, day_str)
            if stage not in ("S1B", "S2"):
                continue

            # Base days check (heavier computation, but only for PPC + right stage)
            df = ind["_df"]
            day_idx_map = df_date_indices.get(symbol, {})
            day_idx = day_idx_map.get(day_str)
            if day_idx is None:
                continue

            base_days, base_quality = _estimate_base_days_at(df, day_idx)
            if base_days < TRADING_RULES["min_base_bars"]:
                continue

            # TRP must be >= 2.0 for tradeable
            trp_pct = ind["trp_pct"].get(day_str, 0)
            if trp_pct < TRADING_RULES["min_trp"]:
                continue

            trigger_level = ind["high"].get(day_str)
            if trigger_level is None:
                continue

            # Signal detected — queue for next-day entry
            pending_entries.append({
                "symbol": symbol,
                "trigger_level": round(trigger_level, 2),
                "signal_date": day_str,
                "trp_pct": round(trp_pct, 2),
            })

        # --- Record equity ---
        mtm = sum(
            (p.remaining_qty or 0) * indicators.get(p.symbol, {}).get("close", {}).get(day_str, p.entry_price or 0)
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
        close_price = ind.get("close", {}).get(last_day, pos.entry_price or 0)
        remaining = pos.remaining_qty or 0
        if remaining > 0:
            entry_price = pos.entry_price or 0
            cash += close_price * remaining
            pos.qty_exited_final = remaining
            pos.remaining_qty = 0
            pos.status = "CLOSED"
            pos.exit_date = date.fromisoformat(last_day)
            total_pnl = _compute_total_pnl(pos, entry_price)
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
    logger.info(
        f"Backtest {run.id} completed: {len(all_trades)} trades, "
        f"{total_return_pct:.2f}% return, {len(trading_days)} days replayed"
    )


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
