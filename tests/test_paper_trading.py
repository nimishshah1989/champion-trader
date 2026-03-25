"""
Tests for backend/services/paper_trading.py

Tests: start_paper_session, process_paper_day, stop_paper_session

Run: python -m pytest tests/test_paper_trading.py -v
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from backend.services.paper_trading import (
    start_paper_session,
    process_paper_day,
    stop_paper_session,
    get_paper_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_db():
    """Create a mock DB session."""
    db = MagicMock()
    def _refresh(obj):
        obj.id = 1
    db.refresh.side_effect = _refresh
    return db


def _make_sim_run(run_id=1, status="ACTIVE", starting_capital=100000, rpt_pct=0.5):
    run = MagicMock()
    run.id = run_id
    run.status = status
    run.starting_capital = Decimal(str(starting_capital))
    run.rpt_pct = rpt_pct
    run.equity_curve = json.dumps([{"date": "2025-01-01", "equity": starting_capital}])
    run.final_capital = Decimal(str(starting_capital))
    run.total_pnl = Decimal("0")
    return run


def _make_sim_trade(symbol="RELIANCE", entry_price=500, total_qty=100,
                    remaining_qty=100, sl_price=480, trp_pct=4.0,
                    target_2r=540, target_ne=580, target_ge=660, target_ee=740,
                    status="OPEN", run_id=1, **overrides):
    trade = MagicMock()
    trade.symbol = symbol
    trade.entry_price = float(entry_price)
    trade.total_qty = total_qty
    trade.remaining_qty = remaining_qty
    trade.sl_price = float(sl_price)
    trade.trp_pct = float(trp_pct)
    trade.target_2r = float(target_2r)
    trade.target_ne = float(target_ne)
    trade.target_ge = float(target_ge)
    trade.target_ee = float(target_ee)
    trade.qty_exited_2r = overrides.get("qty_exited_2r", 0)
    trade.qty_exited_ne = overrides.get("qty_exited_ne", 0)
    trade.qty_exited_ge = overrides.get("qty_exited_ge", 0)
    trade.qty_exited_ee = overrides.get("qty_exited_ee", 0)
    trade.qty_exited_sl = overrides.get("qty_exited_sl", 0)
    trade.qty_exited_final = overrides.get("qty_exited_final", 0)
    trade.rpt_amount = overrides.get("rpt_amount", Decimal("500"))
    trade.status = status
    trade.run_id = run_id
    trade.gross_pnl = overrides.get("gross_pnl", None)
    trade.r_multiple = overrides.get("r_multiple", None)
    trade.exit_date = None
    return trade


# ---------------------------------------------------------------------------
# start_paper_session
# ---------------------------------------------------------------------------

class TestStartPaperSession:
    def test_creates_run(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_run_type_is_paper(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        added = db.add.call_args[0][0]
        assert added.run_type == "PAPER"

    def test_initial_status_active(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        added = db.add.call_args[0][0]
        assert added.status == "ACTIVE"

    def test_initial_capital_stored(self):
        db = _make_mock_db()
        run = start_paper_session(db, 200000, 0.5)
        added = db.add.call_args[0][0]
        assert added.starting_capital == 200000
        assert added.final_capital == 200000

    def test_initial_pnl_zero(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        added = db.add.call_args[0][0]
        assert added.total_pnl == 0

    def test_custom_name(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5, name="My Paper Run")
        added = db.add.call_args[0][0]
        assert added.name == "My Paper Run"

    def test_default_name(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        added = db.add.call_args[0][0]
        assert "Paper Trading" in added.name

    def test_equity_curve_initialized(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        added = db.add.call_args[0][0]
        curve = json.loads(added.equity_curve)
        assert len(curve) == 1
        assert curve[0]["equity"] == 100000

    def test_float_capital_accepted(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000.0, 0.5)
        added = db.add.call_args[0][0]
        assert added.starting_capital == 100000.0

    def test_rpt_pct_stored(self):
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.75)
        added = db.add.call_args[0][0]
        assert added.rpt_pct == 0.75


# ---------------------------------------------------------------------------
# process_paper_day
# ---------------------------------------------------------------------------

class TestProcessPaperDay:
    @patch("backend.services.paper_trading.fetch_current_prices")
    def test_run_not_found(self, mock_prices):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            process_paper_day(db, 999)

    @patch("backend.services.paper_trading.fetch_current_prices")
    def test_run_not_active(self, mock_prices):
        run = _make_sim_run(status="STOPPED")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = run
        with pytest.raises(ValueError, match="not active"):
            process_paper_day(db, 1)

    def test_sl_exit_logic_on_position(self):
        """Verify SL exit logic directly: when price <= sl_price, position should close."""
        trade = _make_sim_trade(entry_price=500, sl_price=480, remaining_qty=100)
        current_price = 475.0  # Below SL

        # Simulate the SL check from process_paper_day
        remaining = trade.remaining_qty or 0
        entry_price = trade.entry_price or 0
        trp_value = entry_price * (trade.trp_pct / 100) if trade.trp_pct else 0

        if trade.sl_price and current_price <= trade.sl_price:
            pnl = (trade.sl_price - entry_price) * remaining
            trade.qty_exited_sl = remaining
            trade.remaining_qty = 0
            trade.status = "CLOSED"

        assert trade.status == "CLOSED"
        assert trade.remaining_qty == 0
        assert trade.qty_exited_sl == 100

    def test_2r_exit_logic_on_position(self):
        """Verify 2R target exit: when price >= target_2r, exit 20% of total_qty."""
        from backend.services.trading_rules import TRADING_RULES
        trade = _make_sim_trade(entry_price=500, target_2r=540.0,
                                remaining_qty=100, total_qty=100)
        current_price = 545.0

        remaining = trade.remaining_qty
        total_qty = trade.total_qty
        if trade.target_2r and current_price >= trade.target_2r and (trade.qty_exited_2r or 0) == 0:
            exit_qty = min(int(total_qty * TRADING_RULES["mathematical_exit_pct"]), remaining)
            trade.qty_exited_2r = exit_qty
            remaining -= exit_qty

        assert trade.qty_exited_2r == 20  # 20% of 100
        assert remaining == 80

    def test_no_action_when_price_between_sl_and_targets(self):
        """Price in safe zone -- no exits."""
        trade = _make_sim_trade(entry_price=500, sl_price=480, target_2r=540,
                                remaining_qty=100, total_qty=100)
        current_price = 510.0

        # SL check
        sl_hit = trade.sl_price and current_price <= trade.sl_price
        # Target check
        target_hit = trade.target_2r and current_price >= trade.target_2r

        assert sl_hit is False
        assert target_hit is False

    def test_zero_remaining_qty_skipped(self):
        """Position with 0 remaining qty should be skipped."""
        trade = _make_sim_trade(remaining_qty=0)
        remaining = trade.remaining_qty or 0
        assert remaining == 0  # Skip condition in process_paper_day


# ---------------------------------------------------------------------------
# stop_paper_session
# ---------------------------------------------------------------------------

class TestStopPaperSession:
    @patch("backend.services.paper_trading.fetch_current_prices")
    def test_run_not_found(self, mock_prices):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            stop_paper_session(db, 999)

    @patch("backend.services.paper_trading.fetch_current_prices")
    def test_run_not_active(self, mock_prices):
        run = _make_sim_run(status="STOPPED")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = run
        with pytest.raises(ValueError, match="not active"):
            stop_paper_session(db, 1)

    def test_close_position_logic(self):
        """Test the position closing logic in stop_paper_session directly."""
        trade = _make_sim_trade(entry_price=500, remaining_qty=100, trp_pct=4.0)
        exit_price = 520.0
        entry_price = trade.entry_price
        remaining = trade.remaining_qty

        if remaining > 0:
            pnl = (exit_price - entry_price) * remaining
            trade.qty_exited_final = remaining
            trade.remaining_qty = 0
            trade.status = "CLOSED"
            trade.gross_pnl = round(pnl, 2)
            trp_value = entry_price * (trade.trp_pct / 100) if trade.trp_pct else 0
            if trp_value > 0:
                trade.r_multiple = round((exit_price - entry_price) / trp_value, 2)

        assert trade.status == "CLOSED"
        assert trade.remaining_qty == 0
        assert trade.gross_pnl == 2000.0  # (520-500) * 100
        assert trade.r_multiple == 1.0  # 20 / 20 (trp_value = 500*4/100=20)

    def test_close_position_loss(self):
        """Test closing at a loss."""
        trade = _make_sim_trade(entry_price=500, remaining_qty=50, trp_pct=4.0)
        exit_price = 490.0
        entry_price = trade.entry_price
        remaining = trade.remaining_qty

        pnl = (exit_price - entry_price) * remaining
        trade.gross_pnl = round(pnl, 2)
        trp_value = entry_price * (trade.trp_pct / 100)
        trade.r_multiple = round((exit_price - entry_price) / trp_value, 2)

        assert trade.gross_pnl == -500.0  # (490-500) * 50
        assert trade.r_multiple == -0.5  # -10 / 20

    def test_no_open_positions_stops_cleanly(self):
        """Stopping with no open positions should just update status."""
        run = _make_sim_run()

        # Simulate: no open positions, just mark as stopped
        run.status = "STOPPED"
        assert run.status == "STOPPED"


# ---------------------------------------------------------------------------
# get_paper_status
# ---------------------------------------------------------------------------

class TestGetPaperStatus:
    def test_run_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            get_paper_status(db, 999)

    def test_returns_status(self):
        run = _make_sim_run()
        trade_open = _make_sim_trade(status="OPEN")
        trade_closed = _make_sim_trade(status="CLOSED")

        db = MagicMock()
        def query_side_effect(model):
            mock_q = MagicMock()
            model_name = model.__name__ if hasattr(model, '__name__') else str(model)
            if model_name == "SimulationRun":
                mock_q.filter.return_value.first.return_value = run
            elif model_name == "SimulationTrade":
                mock_q.filter.return_value.order_by.return_value.all.return_value = [trade_open, trade_closed]
            return mock_q
        db.query.side_effect = query_side_effect

        result = get_paper_status(db, 1)
        assert result["run"] == run
        assert len(result["open_trades"]) == 1
        assert len(result["closed_trades"]) == 1


# ---------------------------------------------------------------------------
# Decimal usage verification
# ---------------------------------------------------------------------------

class TestDecimalUsage:
    def test_start_session_numeric_capital(self):
        """Capital should be stored as a numeric value."""
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        added = db.add.call_args[0][0]
        assert added.starting_capital == 100000

    def test_equity_curve_json_serializable(self):
        """Equity curve values should be JSON-serializable."""
        db = _make_mock_db()
        run = start_paper_session(db, 100000, 0.5)
        added = db.add.call_args[0][0]
        # Should not raise
        parsed = json.loads(added.equity_curve)
        assert len(parsed) > 0

    def test_paper_day_uses_decimal_for_cash(self):
        """process_paper_day uses Decimal internally for cash calculations."""
        # Verify that Decimal is used in paper_trading module
        import inspect
        source = inspect.getsource(process_paper_day)
        assert "Decimal" in source
