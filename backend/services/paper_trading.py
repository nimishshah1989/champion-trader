"""
Paper trading service — forward simulation using real-time prices.
Manual "Process Today" button approach (no background scheduler).
Reuses the same day-processing logic as the backtest engine.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from backend.database import ScanResult, SimulationRun, SimulationTrade
from backend.services.position_calculator import calculate_position
from backend.services.price_monitor import fetch_current_prices
from backend.services.trading_rules import TRADING_RULES

logger = logging.getLogger(__name__)


def start_paper_session(
    db: Session,
    starting_capital: float,
    rpt_pct: float,
    name: str | None = None,
) -> SimulationRun:
    """Create a new paper trading session."""
    run = SimulationRun(
        run_type="PAPER",
        name=name or f"Paper Trading {date.today().isoformat()}",
        starting_capital=starting_capital,
        rpt_pct=rpt_pct,
        start_date=date.today(),
        status="ACTIVE",
        final_capital=starting_capital,
        total_pnl=0,
        total_return_pct=0,
        equity_curve=json.dumps([{
            "date": date.today().isoformat(),
            "equity": starting_capital,
        }]),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def process_paper_day(db: Session, run_id: int) -> dict:
    """
    Process one day of paper trading using current real prices.
    Checks exits on virtual positions, checks today's scan_results for new entries.
    """
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise ValueError(f"Simulation run {run_id} not found")
    if run.status != "ACTIVE":
        raise ValueError(f"Run {run_id} is not active (status: {run.status})")

    today = date.today()
    rpt_pct = run.rpt_pct

    # Get all open positions
    open_positions = (
        db.query(SimulationTrade)
        .filter(
            SimulationTrade.run_id == run_id,
            SimulationTrade.status.in_(["OPEN", "PARTIAL"]),
        )
        .all()
    )

    # Collect all symbols we need
    symbols: set[str] = set()
    for pos in open_positions:
        symbols.add(pos.symbol)

    # Also check today's scan results for new signals
    today_scans = (
        db.query(ScanResult)
        .filter(
            ScanResult.scan_date == today,
            ScanResult.scan_type == "PPC",
        )
        .all()
    )
    for scan in today_scans:
        symbols.add(scan.symbol)

    # Fetch current prices
    prices = fetch_current_prices(list(symbols)) if symbols else {}

    exits_today: list[str] = []
    entries_today: list[str] = []

    # --- Check exits on open positions ---
    for pos in open_positions:
        current_price = prices.get(pos.symbol)
        if current_price is None:
            continue

        remaining = pos.remaining_qty or 0
        if remaining <= 0:
            continue

        entry_price = pos.entry_price or 0
        total_qty = pos.total_qty or remaining
        trp_value = entry_price * (pos.trp_pct / 100) if pos.trp_pct else 0

        # SL check
        if pos.sl_price and current_price <= pos.sl_price:
            pnl = (pos.sl_price - entry_price) * remaining
            pos.qty_exited_sl = remaining
            pos.remaining_qty = 0
            pos.status = "CLOSED"
            pos.exit_date = today
            pos.gross_pnl = round(pnl, 2)
            if trp_value > 0:
                pos.r_multiple = round((pos.sl_price - entry_price) / trp_value, 2)
            pos.pnl_pct = round(((pos.sl_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0
            exits_today.append(f"SL: {pos.symbol} ({remaining} qty)")
            continue

        # Target checks from lowest up
        exited = 0

        if pos.target_2r and current_price >= pos.target_2r and (pos.qty_exited_2r or 0) == 0:
            exit_qty = min(int(total_qty * TRADING_RULES["mathematical_exit_pct"]), remaining)
            if exit_qty > 0:
                pos.qty_exited_2r = exit_qty
                remaining -= exit_qty
                exited += exit_qty
                exits_today.append(f"2R: {pos.symbol} ({exit_qty} qty)")

        if pos.target_ne and current_price >= pos.target_ne and (pos.qty_exited_ne or 0) == 0:
            exit_qty = min(int(total_qty * TRADING_RULES["ne_exit_pct"]), remaining)
            if exit_qty > 0:
                pos.qty_exited_ne = exit_qty
                remaining -= exit_qty
                exited += exit_qty
                exits_today.append(f"NE: {pos.symbol} ({exit_qty} qty)")

        if pos.target_ge and current_price >= pos.target_ge and (pos.qty_exited_ge or 0) == 0:
            exit_qty = min(int(total_qty * TRADING_RULES["ge_exit_pct"]), remaining)
            if exit_qty > 0:
                pos.qty_exited_ge = exit_qty
                remaining -= exit_qty
                exited += exit_qty
                exits_today.append(f"GE: {pos.symbol} ({exit_qty} qty)")

        if pos.target_ee and current_price >= pos.target_ee and (pos.qty_exited_ee or 0) == 0:
            exit_qty = min(int(total_qty * TRADING_RULES["ee_exit_pct"]), remaining)
            if exit_qty > 0:
                pos.qty_exited_ee = exit_qty
                remaining -= exit_qty
                exited += exit_qty
                exits_today.append(f"EE: {pos.symbol} ({exit_qty} qty)")

        pos.remaining_qty = remaining
        if remaining <= 0:
            pos.status = "CLOSED"
            pos.exit_date = today
        elif exited > 0:
            pos.status = "PARTIAL"

    # --- Calculate current cash (starting capital + all realized P&L - cost of open positions) ---
    all_trades = (
        db.query(SimulationTrade)
        .filter(SimulationTrade.run_id == run_id)
        .all()
    )

    total_invested = 0.0
    total_returned = 0.0
    for t in all_trades:
        entry_price = t.entry_price or 0
        total_qty = t.total_qty or 0
        total_invested += entry_price * total_qty

        # Cash returned from exits
        if t.qty_exited_2r and t.target_2r:
            total_returned += t.target_2r * t.qty_exited_2r
        if t.qty_exited_ne and t.target_ne:
            total_returned += t.target_ne * t.qty_exited_ne
        if t.qty_exited_ge and t.target_ge:
            total_returned += t.target_ge * t.qty_exited_ge
        if t.qty_exited_ee and t.target_ee:
            total_returned += t.target_ee * t.qty_exited_ee
        if t.qty_exited_sl and t.sl_price:
            total_returned += t.sl_price * t.qty_exited_sl
        if t.qty_exited_final and t.exit_date:
            # Approximation — use entry price if we don't have exact final exit price
            total_returned += entry_price * t.qty_exited_final

    cash = run.starting_capital - total_invested + total_returned

    # --- Check new signals for entry ---
    existing_symbols = {t.symbol for t in all_trades if t.status in ("OPEN", "PARTIAL")}
    for scan in today_scans:
        if scan.trp is None or scan.trp < TRADING_RULES["min_trp"]:
            continue
        if scan.base_days is not None and scan.base_days < TRADING_RULES["min_base_bars"]:
            continue
        if scan.stage and scan.stage not in ("S1B", "S2"):
            continue
        if scan.trigger_level is None:
            continue
        if scan.symbol in existing_symbols:
            continue

        current_price = prices.get(scan.symbol)
        if current_price is None or current_price < scan.trigger_level:
            continue

        # Calculate equity
        mtm = sum(
            (pos.remaining_qty or 0) * (prices.get(pos.symbol, pos.entry_price or 0))
            for pos in open_positions
        )
        equity = cash + mtm

        # Risk check
        current_risk = sum((pos.rpt_amount or 0) for pos in open_positions if pos.status in ("OPEN", "PARTIAL"))
        max_risk = equity * (TRADING_RULES["max_open_risk_pct"] / 100)

        sizing = calculate_position(equity, rpt_pct, scan.trigger_level, scan.trp)
        if current_risk + sizing["rpt_amount"] > max_risk:
            continue

        position_cost = scan.trigger_level * sizing["position_size"]
        if position_cost > cash:
            continue

        sim_trade = SimulationTrade(
            run_id=run_id,
            symbol=scan.symbol,
            signal_date=today,
            entry_date=today,
            entry_price=scan.trigger_level,
            total_qty=sizing["position_size"],
            half_qty=sizing["half_qty"],
            trp_pct=scan.trp,
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
        cash -= position_cost
        entries_today.append(f"Entry: {scan.symbol} ({sizing['position_size']} qty @ ₹{scan.trigger_level:.2f})")

    # --- Update equity curve ---
    # Refresh open positions list
    current_open = (
        db.query(SimulationTrade)
        .filter(
            SimulationTrade.run_id == run_id,
            SimulationTrade.status.in_(["OPEN", "PARTIAL"]),
        )
        .all()
    )
    mtm = sum(
        (pos.remaining_qty or 0) * prices.get(pos.symbol, pos.entry_price or 0)
        for pos in current_open
    )
    equity = cash + mtm

    # Parse existing equity curve and append
    existing_curve = json.loads(run.equity_curve) if run.equity_curve else []
    existing_curve.append({"date": today.isoformat(), "equity": round(equity, 2)})
    run.equity_curve = json.dumps(existing_curve)

    # Update run summary
    run.final_capital = round(equity, 2)
    run.total_pnl = round(equity - run.starting_capital, 2)
    run.total_return_pct = round(((equity - run.starting_capital) / run.starting_capital) * 100, 2)
    run.last_processed_date = today

    # Count trades
    all_sim_trades = db.query(SimulationTrade).filter(SimulationTrade.run_id == run_id).all()
    closed = [t for t in all_sim_trades if t.status == "CLOSED"]
    wins = [t for t in closed if t.gross_pnl and t.gross_pnl > 0]
    losses = [t for t in closed if t.gross_pnl is not None and t.gross_pnl <= 0]

    run.total_trades = len(all_sim_trades)
    run.win_count = len(wins)
    run.loss_count = len(losses)
    run.win_rate = round(len(wins) / len(closed) * 100, 2) if closed else None

    run.updated_at = datetime.now().isoformat()
    db.commit()

    return {
        "date": today.isoformat(),
        "equity": round(equity, 2),
        "cash": round(cash, 2),
        "entries": entries_today,
        "exits": exits_today,
        "open_positions": len(current_open),
        "prices_fetched": len(prices),
    }


def get_paper_status(db: Session, run_id: int) -> dict:
    """Get current virtual portfolio state for a paper session."""
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise ValueError(f"Simulation run {run_id} not found")

    trades = (
        db.query(SimulationTrade)
        .filter(SimulationTrade.run_id == run_id)
        .order_by(SimulationTrade.entry_date.desc())
        .all()
    )

    open_trades = [t for t in trades if t.status in ("OPEN", "PARTIAL")]
    closed_trades = [t for t in trades if t.status == "CLOSED"]

    return {
        "run": run,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
    }


def stop_paper_session(db: Session, run_id: int) -> SimulationRun:
    """Stop a paper session — close all virtual positions at current prices."""
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if not run:
        raise ValueError(f"Simulation run {run_id} not found")
    if run.status != "ACTIVE":
        raise ValueError(f"Run is not active (status: {run.status})")

    today = date.today()

    # Get open positions
    open_positions = (
        db.query(SimulationTrade)
        .filter(
            SimulationTrade.run_id == run_id,
            SimulationTrade.status.in_(["OPEN", "PARTIAL"]),
        )
        .all()
    )

    # Fetch final prices
    symbols = [p.symbol for p in open_positions]
    prices = fetch_current_prices(symbols) if symbols else {}

    # Close all positions
    for pos in open_positions:
        exit_price = prices.get(pos.symbol, pos.entry_price or 0)
        remaining = pos.remaining_qty or 0
        entry_price = pos.entry_price or 0

        if remaining > 0:
            pnl = (exit_price - entry_price) * remaining
            pos.qty_exited_final = remaining
            pos.remaining_qty = 0
            pos.status = "CLOSED"
            pos.exit_date = today
            pos.gross_pnl = round(pnl, 2)
            trp_value = entry_price * (pos.trp_pct / 100) if pos.trp_pct else 0
            if trp_value > 0:
                pos.r_multiple = round((exit_price - entry_price) / trp_value, 2)
            pos.pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0

    # Compute final stats
    all_trades = db.query(SimulationTrade).filter(SimulationTrade.run_id == run_id).all()
    closed = [t for t in all_trades if t.status == "CLOSED"]
    wins = [t for t in closed if t.gross_pnl and t.gross_pnl > 0]
    losses = [t for t in closed if t.gross_pnl is not None and t.gross_pnl <= 0]

    total_pnl = sum(t.gross_pnl for t in closed if t.gross_pnl) or 0.0

    run.status = "STOPPED"
    run.end_date = today
    run.final_capital = round(run.starting_capital + total_pnl, 2)
    run.total_pnl = round(total_pnl, 2)
    run.total_return_pct = round((total_pnl / run.starting_capital) * 100, 2) if run.starting_capital > 0 else 0
    run.total_trades = len(all_trades)
    run.win_count = len(wins)
    run.loss_count = len(losses)
    run.win_rate = round(len(wins) / len(closed) * 100, 2) if closed else None

    if wins:
        win_rs = [t.r_multiple for t in wins if t.r_multiple is not None]
        if win_rs:
            run.avg_win_r = round(sum(win_rs) / len(win_rs), 2)
    if losses:
        loss_rs = [abs(t.r_multiple) for t in losses if t.r_multiple is not None]
        if loss_rs:
            run.avg_loss_r = round(sum(loss_rs) / len(loss_rs), 2)

    if run.avg_win_r and run.avg_loss_r and run.avg_loss_r > 0:
        run.arr = round(run.avg_win_r / run.avg_loss_r, 2)

    if run.win_rate is not None and run.avg_win_r is not None and run.avg_loss_r is not None:
        win_pct = run.win_rate / 100
        loss_pct = 1 - win_pct
        run.expectancy = round((win_pct * run.avg_win_r) - (loss_pct * run.avg_loss_r), 2)

    run.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(run)
    return run
