"""
Tests for backend/services/autopilot.py

All database interactions are mocked with unittest.mock.
No real DB connection is required.

Run: python -m pytest tests/test_autopilot.py -v
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest

from backend.services.autopilot import (
    VIRTUAL_CAPITAL,
    RPT_PCT,
    MAX_OPEN_RISK_PCT,
    MAX_POSITIONS,
    MIN_TRP,
    post_scan_populate,
    auto_execute_buys,
    auto_execute_sells,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:

    def test_virtual_capital_is_100000(self):
        assert VIRTUAL_CAPITAL == Decimal("100000")

    def test_rpt_pct_is_0_50(self):
        assert RPT_PCT == 0.50

    def test_max_open_risk_pct_is_decimal_10(self):
        assert MAX_OPEN_RISK_PCT == Decimal("10.0")

    def test_max_positions_is_5(self):
        assert MAX_POSITIONS == 5

    def test_min_trp_is_decimal_2(self):
        assert MIN_TRP == Decimal("2.0")

    def test_virtual_capital_is_decimal_type(self):
        assert isinstance(VIRTUAL_CAPITAL, Decimal)

    def test_max_open_risk_pct_is_decimal_type(self):
        assert isinstance(MAX_OPEN_RISK_PCT, Decimal)

    def test_min_trp_is_decimal_type(self):
        assert isinstance(MIN_TRP, Decimal)

    def test_max_risk_amount_equals_10_pct_of_capital(self):
        """₹10,000 is 10% of ₹1,00,000."""
        max_risk = VIRTUAL_CAPITAL * MAX_OPEN_RISK_PCT / Decimal("100")
        assert max_risk == Decimal("10000")


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_scan(
    symbol="RELIANCE",
    trp=3.0,
    watchlist_bucket="READY",
    passes_liquidity_filter=True,
    stage="S2",
    base_days=25,
    base_quality="SMOOTH",
    scan_type="PPC",
    wuc_type="MBB",
    trigger_level=Decimal("500"),
):
    scan = MagicMock()
    scan.symbol = symbol
    scan.trp = Decimal(str(trp))
    scan.watchlist_bucket = watchlist_bucket
    scan.passes_liquidity_filter = passes_liquidity_filter
    scan.stage = stage
    scan.base_days = base_days
    scan.base_quality = base_quality
    scan.scan_type = scan_type
    scan.wuc_type = wuc_type
    scan.trigger_level = trigger_level
    return scan


def _make_trade(symbol="RELIANCE", status="OPEN", rpt_amount=500, remaining_qty=10):
    trade = MagicMock()
    trade.symbol = symbol
    trade.status = status
    trade.rpt_amount = rpt_amount
    trade.remaining_qty = remaining_qty
    trade.avg_entry_price = Decimal("500")
    trade.sl_price = Decimal("480")
    trade.id = 1
    return trade


def _make_alert(
    symbol="RELIANCE",
    alert_category="BUY",
    status="NEW",
    trp_pct=3.0,
    suggested_entry_price=Decimal("500"),
    trigger_price=Decimal("500"),
    exit_qty=None,
    current_price=None,
    trade_id=None,
    alert_type="SL_HIT",
):
    alert = MagicMock()
    alert.symbol = symbol
    alert.alert_category = alert_category
    alert.status = status
    alert.trp_pct = trp_pct
    alert.suggested_entry_price = suggested_entry_price
    alert.trigger_price = trigger_price
    alert.exit_qty = exit_qty
    alert.current_price = current_price
    alert.trade_id = trade_id
    alert.alert_type = alert_type
    alert.created_at = datetime.now()
    return alert


def _make_db(scan_results=(), watchlist=(), open_trades=(), alerts=()):
    """Build a mock Session whose .query().filter().all() chains return controlled data."""
    db = MagicMock()

    def query_side_effect(model):
        from backend.database import ScanResult, Watchlist, Trade, ActionAlert

        mock_query = MagicMock()
        mock_filter = MagicMock()

        if model is ScanResult:
            mock_filter.all.return_value = list(scan_results)
        elif model is Watchlist:
            mock_filter.all.return_value = list(watchlist)
        elif model is Trade:
            mock_filter.all.return_value = list(open_trades)
            mock_filter.filter.return_value = mock_filter
            mock_filter.first.return_value = open_trades[0] if open_trades else None
        elif model is ActionAlert:
            mock_filter.all.return_value = list(alerts)
            mock_filter.filter.return_value = mock_filter
            mock_filter.order_by.return_value = mock_filter

        mock_filter.filter.return_value = mock_filter
        mock_query.filter.return_value = mock_filter
        mock_query.order_by.return_value = mock_filter
        return mock_query

    db.query.side_effect = query_side_effect
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    return db


# ---------------------------------------------------------------------------
# post_scan_populate
# ---------------------------------------------------------------------------

class TestPostScanPopulate:

    def test_returns_zero_when_no_scan_results(self):
        db = _make_db(scan_results=[])
        assert post_scan_populate(db) == 0

    def test_does_not_commit_when_nothing_added(self):
        db = _make_db(scan_results=[])
        post_scan_populate(db)
        db.commit.assert_not_called()

    def test_filters_out_stock_below_min_trp(self):
        scan = _make_scan(symbol="LOW_TRP", trp=1.5)  # below MIN_TRP=2.0
        db = _make_db(scan_results=[scan])
        result = post_scan_populate(db)
        assert result == 0
        db.add.assert_not_called()

    def test_filters_out_stock_already_on_watchlist(self):
        scan = _make_scan(symbol="RELIANCE", trp=3.0)
        existing = MagicMock()
        existing.symbol = "RELIANCE"
        existing.status = "ACTIVE"
        db = _make_db(scan_results=[scan], watchlist=[existing])
        result = post_scan_populate(db)
        assert result == 0

    def test_filters_out_stock_already_in_open_trade(self):
        scan = _make_scan(symbol="RELIANCE", trp=3.0)
        trade = _make_trade(symbol="RELIANCE", status="OPEN")
        db = _make_db(scan_results=[scan], open_trades=[trade])
        result = post_scan_populate(db)
        assert result == 0

    def test_filters_out_away_bucket_stocks(self):
        scan = _make_scan(symbol="AWAY_STOCK", trp=3.0, watchlist_bucket="AWAY")
        db = _make_db(scan_results=[scan])
        result = post_scan_populate(db)
        assert result == 0

    def test_filters_out_illiquid_stocks(self):
        scan = _make_scan(symbol="ILLIQUID", trp=3.0, passes_liquidity_filter=False)
        db = _make_db(scan_results=[scan])
        result = post_scan_populate(db)
        assert result == 0

    def test_adds_ready_stock_meeting_all_criteria(self):
        scan = _make_scan(symbol="GOOD_STOCK", trp=3.0, watchlist_bucket="READY")
        db = _make_db(scan_results=[scan])
        result = post_scan_populate(db)
        assert result == 1
        db.add.assert_called_once()

    def test_adds_near_stock_meeting_all_criteria(self):
        scan = _make_scan(symbol="NEAR_STOCK", trp=2.5, watchlist_bucket="NEAR")
        db = _make_db(scan_results=[scan])
        result = post_scan_populate(db)
        assert result == 1
        db.add.assert_called_once()

    def test_commits_when_stocks_added(self):
        scan = _make_scan(symbol="GOOD_STOCK", trp=3.0, watchlist_bucket="READY")
        db = _make_db(scan_results=[scan])
        post_scan_populate(db)
        db.commit.assert_called_once()

    def test_stock_at_exact_min_trp_boundary_is_accepted(self):
        """TRP exactly equal to MIN_TRP (2.0) should NOT be filtered out."""
        scan = _make_scan(symbol="EDGE_TRP", trp=2.0, watchlist_bucket="READY")
        db = _make_db(scan_results=[scan])
        result = post_scan_populate(db)
        assert result == 1

    def test_duplicate_symbol_in_scan_results_added_only_once(self):
        scan1 = _make_scan(symbol="RELIANCE", trp=3.0, watchlist_bucket="READY")
        scan2 = _make_scan(symbol="RELIANCE", trp=3.0, watchlist_bucket="READY")
        db = _make_db(scan_results=[scan1, scan2])
        result = post_scan_populate(db)
        # Second occurrence should be skipped (symbol already in existing_symbols set)
        assert result == 1


# ---------------------------------------------------------------------------
# auto_execute_buys
# ---------------------------------------------------------------------------

class TestAutoExecuteBuys:

    def test_returns_zero_when_max_positions_reached(self):
        open_trades = [_make_trade(rpt_amount=500) for _ in range(MAX_POSITIONS)]
        db = _make_db(open_trades=open_trades)
        result = auto_execute_buys(db)
        assert result == 0

    def test_does_not_commit_when_max_positions_reached(self):
        open_trades = [_make_trade(rpt_amount=500) for _ in range(MAX_POSITIONS)]
        db = _make_db(open_trades=open_trades)
        auto_execute_buys(db)
        db.commit.assert_not_called()

    def test_returns_zero_when_no_buy_alerts(self):
        db = _make_db(open_trades=[], alerts=[])
        result = auto_execute_buys(db)
        assert result == 0

    def test_filters_alert_with_trp_below_min(self):
        alert = _make_alert(trp_pct=1.5)  # below MIN_TRP=2.0
        db = _make_db(open_trades=[], alerts=[alert])
        result = auto_execute_buys(db)
        assert result == 0
        assert alert.status == "DISMISSED"

    def test_filters_alert_with_none_trp(self):
        alert = _make_alert(trp_pct=None)
        db = _make_db(open_trades=[], alerts=[alert])
        result = auto_execute_buys(db)
        assert result == 0

    def test_executes_valid_buy_alert(self):
        alert = _make_alert(
            symbol="RELIANCE",
            trp_pct=3.18,
            suggested_entry_price=Decimal("601"),
        )
        db = _make_db(open_trades=[], alerts=[alert])
        with patch("backend.services.autopilot.get_latest_regime", return_value={"regime": "BULL"}):
            result = auto_execute_buys(db)
        assert result == 1
        db.add.assert_called()
        db.commit.assert_called_once()

    def test_marks_alert_as_acted_on_execution(self):
        alert = _make_alert(
            trp_pct=3.18,
            suggested_entry_price=Decimal("601"),
        )
        db = _make_db(open_trades=[], alerts=[alert])
        with patch("backend.services.autopilot.get_latest_regime", return_value={"regime": "BULL"}):
            auto_execute_buys(db)
        assert alert.status == "ACTED"

    def test_stops_when_position_limit_hit_mid_loop(self):
        """If MAX_POSITIONS - 1 trades open, only 1 more alert should execute."""
        open_trades = [_make_trade(rpt_amount=100) for _ in range(MAX_POSITIONS - 1)]
        alert1 = _make_alert(symbol="STOCK1", trp_pct=3.0, suggested_entry_price=Decimal("200"))
        alert2 = _make_alert(symbol="STOCK2", trp_pct=3.0, suggested_entry_price=Decimal("200"))
        db = _make_db(open_trades=open_trades, alerts=[alert1, alert2])
        with patch("backend.services.autopilot.get_latest_regime", return_value={"regime": "BULL"}):
            result = auto_execute_buys(db)
        assert result == 1

    def test_skips_alert_with_no_entry_price(self):
        alert = _make_alert(
            trp_pct=3.0,
            suggested_entry_price=None,
            trigger_price=None,
        )
        db = _make_db(open_trades=[], alerts=[alert])
        result = auto_execute_buys(db)
        assert result == 0

    def test_risk_is_calculated_using_decimal_not_float(self):
        """Verify that rpt_amount in open_trades is summed as Decimal."""
        # Each trade has rpt_amount=400 — total = 400 (well below ₹10,000 limit)
        open_trade = _make_trade(rpt_amount=400, status="OPEN")
        alert = _make_alert(
            trp_pct=3.0,
            suggested_entry_price=Decimal("100"),
        )
        db = _make_db(open_trades=[open_trade], alerts=[alert])
        with patch("backend.services.autopilot.get_latest_regime", return_value={"regime": "BULL"}):
            result = auto_execute_buys(db)
        # Should execute — ₹400 current risk + small new risk < ₹10,000 limit
        assert result == 1


# ---------------------------------------------------------------------------
# auto_execute_sells
# ---------------------------------------------------------------------------

class TestAutoExecuteSells:

    def test_returns_zero_when_no_sell_alerts(self):
        db = _make_db(alerts=[])
        result = auto_execute_sells(db)
        assert result == 0

    def test_skips_alert_with_no_trade_id(self):
        alert = _make_alert(alert_category="SELL", trade_id=None)
        db = _make_db(alerts=[alert])
        result = auto_execute_sells(db)
        assert result == 0

    def test_dismisses_alert_when_trade_not_found(self):
        alert = _make_alert(alert_category="SELL", trade_id=99)
        db = MagicMock()
        # query chain returns None for the trade lookup
        mock_chain = MagicMock()
        mock_chain.filter.return_value.all.return_value = [alert]
        mock_chain.filter.return_value.order_by.return_value.all.return_value = [alert]
        mock_chain.filter.return_value.first.return_value = None
        db.query.return_value = mock_chain
        result = auto_execute_sells(db)
        assert alert.status == "DISMISSED"

    def test_sl_hit_closes_entire_remaining_quantity(self):
        """An SL hit should exit all remaining qty and set status to CLOSED."""
        trade = _make_trade(symbol="RELIANCE", status="OPEN", remaining_qty=131)
        trade.avg_entry_price = Decimal("601")
        trade.sl_price = Decimal("582")

        alert = _make_alert(
            alert_category="SELL",
            trade_id=1,
            alert_type="SL_HIT",
            exit_qty=131,
            trigger_price=Decimal("580"),
        )

        db = MagicMock()
        # Wire up the query chain for ScanResult/Watchlist/Trade/ActionAlert
        sell_chain = MagicMock()
        sell_chain.filter.return_value.order_by.return_value.all.return_value = [alert]

        trade_chain = MagicMock()
        trade_chain.filter.return_value.first.return_value = trade

        def query_dispatch(model):
            from backend.database import ActionAlert, Trade
            if model is ActionAlert:
                return sell_chain
            if model is Trade:
                return trade_chain
            return MagicMock()

        db.query.side_effect = query_dispatch
        db.commit = MagicMock()

        result = auto_execute_sells(db)
        assert result == 1
        assert trade.status == "CLOSED"
        assert trade.remaining_qty == 0

    def test_partial_exit_sets_status_to_partial(self):
        """Exiting half the position should set status to PARTIAL."""
        trade = _make_trade(symbol="RELIANCE", status="OPEN", remaining_qty=100)
        trade.avg_entry_price = Decimal("500")
        trade.sl_price = Decimal("480")

        alert = _make_alert(
            alert_category="SELL",
            trade_id=1,
            alert_type="2R_HIT",
            exit_qty=20,   # partial exit (20 out of 100)
            trigger_price=Decimal("520"),
        )

        db = MagicMock()
        sell_chain = MagicMock()
        sell_chain.filter.return_value.order_by.return_value.all.return_value = [alert]

        trade_chain = MagicMock()
        trade_chain.filter.return_value.first.return_value = trade

        def query_dispatch(model):
            from backend.database import ActionAlert, Trade
            if model is ActionAlert:
                return sell_chain
            if model is Trade:
                return trade_chain
            return MagicMock()

        db.query.side_effect = query_dispatch
        db.commit = MagicMock()

        result = auto_execute_sells(db)
        assert result == 1
        assert trade.status == "PARTIAL"
        assert trade.remaining_qty == 80

    def test_skips_alert_with_none_exit_price(self):
        """When both trigger_price and current_price are None the alert is skipped."""
        trade = _make_trade(symbol="RELIANCE", status="OPEN", remaining_qty=100)
        trade.avg_entry_price = Decimal("500")
        trade.sl_price = Decimal("480")

        alert = _make_alert(
            alert_category="SELL",
            trade_id=1,
            exit_qty=None,
            trigger_price=None,
            current_price=None,
        )

        db = MagicMock()
        sell_chain = MagicMock()
        sell_chain.filter.return_value.order_by.return_value.all.return_value = [alert]

        trade_chain = MagicMock()
        trade_chain.filter.return_value.first.return_value = trade

        def query_dispatch(model):
            from backend.database import ActionAlert, Trade
            if model is ActionAlert:
                return sell_chain
            if model is Trade:
                return trade_chain
            return MagicMock()

        db.query.side_effect = query_dispatch

        result = auto_execute_sells(db)
        assert result == 0

    def test_marks_sell_alert_as_acted(self):
        trade = _make_trade(symbol="RELIANCE", status="OPEN", remaining_qty=50)
        trade.avg_entry_price = Decimal("500")
        trade.sl_price = Decimal("480")

        alert = _make_alert(
            alert_category="SELL",
            trade_id=1,
            exit_qty=50,
            trigger_price=Decimal("510"),
        )

        db = MagicMock()
        sell_chain = MagicMock()
        sell_chain.filter.return_value.order_by.return_value.all.return_value = [alert]

        trade_chain = MagicMock()
        trade_chain.filter.return_value.first.return_value = trade

        def query_dispatch(model):
            from backend.database import ActionAlert, Trade
            if model is ActionAlert:
                return sell_chain
            if model is Trade:
                return trade_chain
            return MagicMock()

        db.query.side_effect = query_dispatch
        db.commit = MagicMock()

        auto_execute_sells(db)
        assert alert.status == "ACTED"

    def test_commits_when_exits_executed(self):
        trade = _make_trade(symbol="RELIANCE", status="OPEN", remaining_qty=100)
        trade.avg_entry_price = Decimal("500")
        trade.sl_price = Decimal("480")

        alert = _make_alert(
            alert_category="SELL",
            trade_id=1,
            exit_qty=100,
            trigger_price=Decimal("510"),
        )

        db = MagicMock()
        sell_chain = MagicMock()
        sell_chain.filter.return_value.order_by.return_value.all.return_value = [alert]

        trade_chain = MagicMock()
        trade_chain.filter.return_value.first.return_value = trade

        def query_dispatch(model):
            from backend.database import ActionAlert, Trade
            if model is ActionAlert:
                return sell_chain
            if model is Trade:
                return trade_chain
            return MagicMock()

        db.query.side_effect = query_dispatch
        db.commit = MagicMock()

        auto_execute_sells(db)
        db.commit.assert_called_once()

    def test_dismisses_alert_for_already_closed_trade(self):
        trade = _make_trade(symbol="RELIANCE", status="CLOSED", remaining_qty=0)
        alert = _make_alert(alert_category="SELL", trade_id=1)

        db = MagicMock()
        sell_chain = MagicMock()
        sell_chain.filter.return_value.order_by.return_value.all.return_value = [alert]

        trade_chain = MagicMock()
        trade_chain.filter.return_value.first.return_value = trade

        def query_dispatch(model):
            from backend.database import ActionAlert, Trade
            if model is ActionAlert:
                return sell_chain
            if model is Trade:
                return trade_chain
            return MagicMock()

        db.query.side_effect = query_dispatch

        result = auto_execute_sells(db)
        assert result == 0
        assert alert.status == "DISMISSED"
