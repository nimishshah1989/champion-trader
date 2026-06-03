"""
RS Backtest Engine — tests Relative Strength crossover strategy against Nifty 50 benchmark.

Three scenarios (all share one data-fetch pass):

  RS_ONLY     — Buy when SMA20(RS) crosses above SMA200(RS).
                Sell when it crosses back below. Hard SL at stop_loss_pct%.

  DUAL_EITHER — Buy when BOTH price SMA20>SMA200 AND RS SMA20>RS SMA200 become true
                simultaneously. Sell when EITHER crossover reverses. Hard SL.

  DUAL_BOTH   — Same dual buy condition.
                Sell only when BOTH crossovers have reversed to bearish. Hard SL.

RS = Stock Close / Nifty 50 Close (daily ratio, dimensionless).
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from backend.data.nse_stocks import get_yfinance_symbols, strip_ns_suffix
from backend.database import SessionLocal, SimulationRun, SimulationTrade

logger = logging.getLogger(__name__)

NIFTY_TICKER = "^NSEI"
BUFFER_DAYS = 400          # calendar days before start_date to warm up SMA200
BATCH_SIZE = 50
DEFAULT_SL_PCT = 8.0
DEFAULT_MAX_POSITIONS = 10
YFINANCE_TIMEOUT = 120

VALID_SCENARIOS = ["RS_ONLY", "DUAL_EITHER", "DUAL_BOTH"]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_rs_backtest(
    db: Session,
    start_date: date,
    end_date: date,
    starting_capital: float,
    rpt_pct: float = 0.5,
    stop_loss_pct: float = DEFAULT_SL_PCT,
    max_positions: int = DEFAULT_MAX_POSITIONS,
    name: str | None = None,
) -> dict[str, SimulationRun]:
    """
    Create SimulationRun records for all three RS scenarios and launch the
    backtest in a background thread. Returns immediately with RUNNING status.
    """
    runs: dict[str, SimulationRun] = {}
    label = name or f"RS Backtest {start_date} → {end_date}"

    for scenario in VALID_SCENARIOS:
        run = SimulationRun(
            run_type=scenario,
            name=f"{label} [{scenario}]",
            starting_capital=starting_capital,
            rpt_pct=rpt_pct,
            start_date=start_date,
            end_date=end_date,
            status="RUNNING",
            error_message=json.dumps({"phase": "starting", "progress_pct": 0}),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        runs[scenario] = run

    run_ids = {s: r.id for s, r in runs.items()}
    thread = threading.Thread(
        target=_background,
        args=(run_ids, start_date, end_date, starting_capital, rpt_pct, stop_loss_pct, max_positions),
        daemon=True,
    )
    thread.start()
    return runs


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _background(
    run_ids: dict[str, int],
    start_date: date,
    end_date: date,
    starting_capital: float,
    rpt_pct: float,
    stop_loss_pct: float,
    max_positions: int,
) -> None:
    db = SessionLocal(expire_on_commit=False)
    try:
        _update_progress(db, run_ids, "fetching_nifty", 5)
        fetch_start = (start_date - timedelta(days=BUFFER_DAYS)).strftime("%Y-%m-%d")
        fetch_end   = (end_date + timedelta(days=5)).strftime("%Y-%m-%d")

        nifty_close = _fetch_nifty(fetch_start, fetch_end)
        if nifty_close is None or len(nifty_close) < 210:
            _fail_all(db, run_ids, "Nifty 50 data insufficient (need 210+ trading days)")
            return

        _update_progress(db, run_ids, "fetching_stocks", 10)
        stock_data = _fetch_stocks(get_yfinance_symbols(), fetch_start, fetch_end)
        logger.info(f"[RS] {len(stock_data)} stocks fetched")

        _update_progress(db, run_ids, "computing_signals", 30)
        signals = _compute_signals(stock_data, nifty_close)
        trading_days = _trading_days_in_range(nifty_close, start_date, end_date)
        logger.info(f"[RS] {len(signals)} stocks with signals | {len(trading_days)} trading days")

        for idx, scenario in enumerate(VALID_SCENARIOS):
            pct = 50 + idx * 15
            _update_progress(db, run_ids, f"simulating_{scenario}", pct)
            _simulate(
                db, run_ids[scenario], scenario, signals, trading_days,
                starting_capital, rpt_pct, stop_loss_pct, max_positions,
                start_date, end_date,
            )

        logger.info("[RS] All scenarios complete")

    except Exception as exc:
        logger.exception(f"[RS] Fatal error: {exc}")
        _fail_all(db, run_ids, str(exc)[:500])
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _fetch_nifty(fetch_start: str, fetch_end: str) -> pd.Series | None:
    try:
        df = yf.download(
            NIFTY_TICKER, start=fetch_start, end=fetch_end,
            auto_adjust=True, progress=False, timeout=60,
        )
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index).normalize()
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close.dropna()
    except Exception as exc:
        logger.error(f"Nifty fetch failed: {exc}")
        return None


def _fetch_stocks(symbols: list[str], fetch_start: str, fetch_end: str) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    batches = [symbols[i:i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]
    for batch_idx, batch in enumerate(batches):
        logger.info(f"[RS] Stock batch {batch_idx + 1}/{len(batches)}")
        try:
            raw = yf.download(
                tickers=batch, start=fetch_start, end=fetch_end,
                group_by="ticker", auto_adjust=True,
                threads=True, progress=False, timeout=YFINANCE_TIMEOUT,
            )
            if raw.empty:
                continue
            for yf_sym in batch:
                clean = strip_ns_suffix(yf_sym)
                try:
                    df = raw[yf_sym] if len(batch) > 1 else raw
                    df = df.dropna(subset=["Close"])
                    df.index = pd.to_datetime(df.index).normalize()
                    if len(df) >= 210:
                        result[clean] = df[["Open", "High", "Low", "Close"]]
                except (KeyError, TypeError):
                    pass
        except Exception as exc:
            logger.error(f"Stock batch {batch_idx + 1} failed: {exc}")
    return result


# ---------------------------------------------------------------------------
# Signal pre-computation
# ---------------------------------------------------------------------------

def _compute_signals(
    stock_data: dict[str, pd.DataFrame],
    nifty_close: pd.Series,
) -> dict[str, dict[str, dict]]:
    """
    Pre-compute per-day signal fields for every stock.
    Returns {symbol: {date_str: signal_dict}}.
    """
    signals: dict[str, dict[str, dict]] = {}

    for sym, df in stock_data.items():
        try:
            common = df.index.intersection(nifty_close.index)
            if len(common) < 210:
                continue

            sc = df.loc[common, "Close"]
            so = df.loc[common, "Open"]
            sh = df.loc[common, "High"]
            sl = df.loc[common, "Low"]
            nc = nifty_close.loc[common]

            rs = sc / nc
            p20  = sc.rolling(20).mean()
            p200 = sc.rolling(200).mean()
            r20  = rs.rolling(20).mean()
            r200 = rs.rolling(200).mean()

            sym_sig: dict[str, dict] = {}
            for i in range(201, len(common)):
                if (pd.isna(p20.iloc[i])  or pd.isna(p200.iloc[i]) or
                    pd.isna(r20.iloc[i])  or pd.isna(r200.iloc[i]) or
                    pd.isna(p20.iloc[i-1]) or pd.isna(p200.iloc[i-1]) or
                    pd.isna(r20.iloc[i-1]) or pd.isna(r200.iloc[i-1])):
                    continue

                dt = common[i]
                sym_sig[dt.strftime("%Y-%m-%d")] = {
                    "open":  float(so.iloc[i]),
                    "high":  float(sh.iloc[i]),
                    "low":   float(sl.iloc[i]),
                    "close": float(sc.iloc[i]),
                    # today
                    "p20":   float(p20.iloc[i]),
                    "p200":  float(p200.iloc[i]),
                    "r20":   float(r20.iloc[i]),
                    "r200":  float(r200.iloc[i]),
                    # yesterday (for crossover detection)
                    "pp20":  float(p20.iloc[i-1]),
                    "pp200": float(p200.iloc[i-1]),
                    "pr20":  float(r20.iloc[i-1]),
                    "pr200": float(r200.iloc[i-1]),
                }
            if sym_sig:
                signals[sym] = sym_sig
        except Exception as exc:
            logger.debug(f"[RS] Signal skipped {sym}: {exc}")

    return signals


def _trading_days_in_range(nifty_close: pd.Series, start: date, end: date) -> list[str]:
    return sorted(
        d.strftime("%Y-%m-%d")
        for d in nifty_close.index
        if start <= d.date() <= end
    )


# ---------------------------------------------------------------------------
# Signal logic per scenario
# ---------------------------------------------------------------------------

def _is_buy(d: dict, scenario: str) -> bool:
    """True on the exact day the buy crossover fires."""
    rs_up = d["pr20"] <= d["pr200"] and d["r20"] > d["r200"]   # RS golden cross today

    if scenario == "RS_ONLY":
        return rs_up

    # DUAL: both must be bullish today, and at least one just transitioned
    both_bull_today = d["p20"] > d["p200"] and d["r20"] > d["r200"]
    if not both_bull_today:
        return False
    prev_not_both = d["pp20"] <= d["pp200"] or d["pr20"] <= d["pr200"]
    return prev_not_both


def _is_sell(d: dict, scenario: str) -> bool:
    """True on the exact day the exit crossover fires (SL handled separately)."""
    rs_dn = d["pr20"] >= d["pr200"] and d["r20"] < d["r200"]   # RS death cross today
    p_dn  = d["pp20"] >= d["pp200"] and d["p20"] < d["p200"]   # Price death cross today

    if scenario == "RS_ONLY":
        return rs_dn

    if scenario == "DUAL_EITHER":
        return rs_dn or p_dn

    # DUAL_BOTH: sell when both are bearish today and at least one just turned
    both_bear = d["p20"] < d["p200"] and d["r20"] < d["r200"]
    if not both_bear:
        return False
    prev_not_both_bear = d["pp20"] >= d["pp200"] or d["pr20"] >= d["pr200"]
    return prev_not_both_bear


# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------

def _simulate(
    db: Session,
    run_id: int,
    scenario: str,
    signals: dict[str, dict[str, dict]],
    trading_days: list[str],
    starting_capital: float,
    rpt_pct: float,
    stop_loss_pct: float,
    max_positions: int,
    start_date: date,
    end_date: date,
) -> None:
    sl_frac   = stop_loss_pct / 100.0
    risk_frac = rpt_pct / 100.0

    cash = starting_capital
    # {sym: {entry_price, qty, sl_price, entry_date, signal_date, portfolio_value_at_entry}}
    positions: dict[str, dict] = {}
    pending_buys: dict[str, str] = {}    # sym → signal_date_str
    pending_sells: set[str] = set()
    equity_curve: list[dict] = []
    closed_trades: list[dict] = []

    for day_str in trading_days:
        # 1. Execute pending entries at today's open
        if pending_buys:
            for sym, sig_date in list(pending_buys.items()):
                if sym in positions or len(positions) >= max_positions:
                    continue
                d = signals.get(sym, {}).get(day_str)
                if not d or d["open"] <= 0:
                    continue

                entry = d["open"]
                sl    = entry * (1.0 - sl_frac)
                risk_unit = entry - sl
                if risk_unit <= 0:
                    continue

                port_val  = _portfolio_value(cash, positions, day_str, signals)
                risk_amt  = port_val * risk_frac
                qty = int(risk_amt / risk_unit)
                if qty <= 0:
                    continue
                if qty * entry > cash:
                    qty = int(cash / entry)
                if qty <= 0:
                    continue

                cash -= qty * entry
                positions[sym] = {
                    "entry_price": entry,
                    "qty": qty,
                    "sl_price": sl,
                    "entry_date": day_str,
                    "signal_date": sig_date,
                    "portfolio_value_at_entry": port_val,
                }
            pending_buys.clear()

        # 2. Execute pending sells at today's open
        for sym in list(pending_sells):
            if sym not in positions:
                continue
            d   = signals.get(sym, {}).get(day_str)
            pos = positions.pop(sym)
            exit_price = d["open"] if d and d["open"] > 0 else pos["entry_price"]
            cash += pos["qty"] * exit_price
            closed_trades.append(_make_trade(sym, pos, exit_price, day_str, "SIGNAL"))
        pending_sells.clear()

        # 3. Check SL (gap-down or intraday)
        for sym in list(positions.keys()):
            d = signals.get(sym, {}).get(day_str)
            if not d:
                continue
            pos = positions[sym]
            if d["open"] < pos["sl_price"]:
                exit_price = d["open"]            # gapped through SL
            elif d["low"] <= pos["sl_price"]:
                exit_price = pos["sl_price"]      # intraday SL touch
            else:
                continue
            cash += pos["qty"] * exit_price
            closed_trades.append(_make_trade(sym, pos, exit_price, day_str, "SL"))
            del positions[sym]

        # 4. End-of-day signal scan
        for sym, sym_signals in signals.items():
            d = sym_signals.get(day_str)
            if not d:
                continue
            if sym in positions:
                if _is_sell(d, scenario) and sym not in pending_sells:
                    pending_sells.add(sym)
            elif sym not in pending_buys and len(positions) + len(pending_buys) < max_positions:
                if _is_buy(d, scenario):
                    pending_buys[sym] = day_str

        # 5. EOD equity mark
        equity_curve.append({
            "date": day_str,
            "equity": round(_portfolio_value(cash, positions, day_str, signals), 2),
        })

    # Force-close remaining at end of backtest
    last_day = trading_days[-1] if trading_days else None
    for sym, pos in list(positions.items()):
        d = signals.get(sym, {}).get(last_day) if last_day else None
        exit_price = d["close"] if d and d["close"] > 0 else pos["entry_price"]
        cash += pos["qty"] * exit_price
        closed_trades.append(_make_trade(sym, pos, exit_price, last_day, "EOB"))

    _save_results(db, run_id, closed_trades, equity_curve, starting_capital, start_date, end_date)


def _portfolio_value(
    cash: float,
    positions: dict[str, dict],
    day_str: str,
    signals: dict[str, dict[str, dict]],
) -> float:
    val = cash
    for sym, pos in positions.items():
        d = signals.get(sym, {}).get(day_str)
        price = d["close"] if d and d["close"] > 0 else pos["entry_price"]
        val += pos["qty"] * price
    return val


def _make_trade(sym: str, pos: dict, exit_price: float, exit_date: str, reason: str) -> dict:
    qty      = pos["qty"]
    entry    = pos["entry_price"]
    sl       = pos["sl_price"]
    pnl      = (exit_price - entry) * qty
    pnl_pct  = (exit_price - entry) / entry * 100
    r_risk   = (entry - sl) * qty
    r_mult   = pnl / r_risk if r_risk != 0 else 0.0
    return {
        "symbol":                   sym,
        "signal_date":              pos["signal_date"],
        "entry_date":               pos["entry_date"],
        "exit_date":                exit_date,
        "entry_price":              entry,
        "exit_price":               exit_price,
        "qty":                      qty,
        "sl_price":                 sl,
        "gross_pnl":                pnl,
        "pnl_pct":                  pnl_pct,
        "r_multiple":               r_mult,
        "exit_reason":              reason,
        "portfolio_value_at_entry": pos["portfolio_value_at_entry"],
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _save_results(
    db: Session,
    run_id: int,
    closed_trades: list[dict],
    equity_curve: list[dict],
    starting_capital: float,
    start_date: date,
    end_date: date,
) -> None:
    wins   = [t for t in closed_trades if t["gross_pnl"] > 0]
    losses = [t for t in closed_trades if t["gross_pnl"] <= 0]
    total  = len(closed_trades)

    final_equity    = equity_curve[-1]["equity"] if equity_curve else starting_capital
    total_pnl       = final_equity - starting_capital
    total_ret_pct   = total_pnl / starting_capital * 100 if starting_capital else 0
    win_rate        = len(wins) / total * 100 if total else 0
    avg_win_pct     = sum(t["pnl_pct"] for t in wins)   / len(wins)   if wins   else 0
    avg_loss_pct    = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    expectancy      = (win_rate / 100 * avg_win_pct) + ((1 - win_rate / 100) * avg_loss_pct)
    max_dd          = _max_drawdown(equity_curve)
    n_days          = (end_date - start_date).days
    arr             = ((final_equity / starting_capital) ** (365.0 / n_days) - 1) * 100 \
                      if n_days > 0 and starting_capital > 0 else 0

    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        return

    run.status              = "COMPLETED"
    run.error_message       = None
    run.final_capital       = Decimal(str(round(final_equity, 2)))
    run.total_pnl           = Decimal(str(round(total_pnl, 2)))
    run.total_return_pct    = round(total_ret_pct, 4)
    run.total_trades        = total
    run.win_count           = len(wins)
    run.loss_count          = len(losses)
    run.win_rate            = round(win_rate, 2)
    run.avg_win_r           = round(avg_win_pct, 4)
    run.avg_loss_r          = round(avg_loss_pct, 4)
    run.arr                 = round(arr, 4)
    run.expectancy          = round(expectancy, 4)
    run.max_drawdown_pct    = round(max_dd, 4)
    run.max_drawdown_amount = Decimal(str(round(max_dd / 100 * starting_capital, 2)))
    run.equity_curve        = json.dumps(equity_curve)
    run.updated_at          = datetime.now().isoformat()
    db.commit()

    for t in closed_trades:
        trade = SimulationTrade(
            run_id        = run_id,
            symbol        = t["symbol"],
            signal_date   = _parse_date(t["signal_date"]),
            entry_date    = _parse_date(t["entry_date"]),
            exit_date     = _parse_date(t["exit_date"]),
            entry_price   = Decimal(str(round(t["entry_price"], 4))),
            total_qty     = t["qty"],
            sl_price      = Decimal(str(round(t["sl_price"], 4))),
            qty_exited_sl    = t["qty"] if t["exit_reason"] == "SL" else 0,
            qty_exited_final = t["qty"] if t["exit_reason"] != "SL" else 0,
            status        = "CLOSED",
            gross_pnl     = Decimal(str(round(t["gross_pnl"], 2))),
            r_multiple    = round(t["r_multiple"], 4),
            pnl_pct       = round(t["pnl_pct"], 4),
            portfolio_value_at_entry = Decimal(str(round(t["portfolio_value_at_entry"], 2))),
        )
        db.add(trade)

    db.commit()
    logger.info(
        f"[RS] Run {run_id} complete — {total} trades | "
        f"win {win_rate:.1f}% | ARR {arr:.1f}% | max_dd {max_dd:.1f}%"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _max_drawdown(equity_curve: list[dict]) -> float:
    peak = 0.0
    max_dd = 0.0
    for pt in equity_curve:
        eq = float(pt["equity"])
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _update_progress(db: Session, run_ids: dict[str, int], phase: str, pct: int) -> None:
    payload = json.dumps({"phase": phase, "progress_pct": pct})
    for run_id in run_ids.values():
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if run and run.status == "RUNNING":
            run.error_message = payload
            run.updated_at    = datetime.now().isoformat()
    db.commit()


def _fail_all(db: Session, run_ids: dict[str, int], reason: str) -> None:
    for run_id in run_ids.values():
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if run:
            run.status        = "FAILED"
            run.error_message = reason
            run.updated_at    = datetime.now().isoformat()
    db.commit()
