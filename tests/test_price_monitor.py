"""
Tests for backend/services/price_monitor.py

Tests: check_buy_signals, check_sell_signals, is_entry_window,
       fetch_current_prices (mocked), _write_check_log

Run: python -m pytest tests/test_price_monitor.py -v
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.services.price_monitor import (
    check_buy_signals,
    check_sell_signals,
    fetch_current_prices,
    is_entry_window,
    _write_check_log,
)
from backend.services.trading_rules import TRADING_RULES


# ---------------------------------------------------------------------------
# is_entry_window
# ---------------------------------------------------------------------------

class TestIsEntryWindow:
    @patch("backend.services.price_monitor.datetime")
    def test_inside_window(self, mock_dt):
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
        mock_dt.now.return_value = datetime(2025, 3, 15, 15, 10, tzinfo=IST)
        assert is_entry_window() is True

    @patch("backend.services.price_monitor.datetime")
    def test_before_window(self, mock_dt):
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
        mock_dt.now.return_value = datetime(2025, 3, 15, 14, 30, tzinfo=IST)
        assert is_entry_window() is False

    @patch("backend.services.price_monitor.datetime")
    def test_after_window(self, mock_dt):
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
        mock_dt.now.return_value = datetime(2025, 3, 15, 15, 45, tzinfo=IST)
        assert is_entry_window() is False

    @patch("backend.services.price_monitor.datetime")
    def test_window_start_boundary(self, mock_dt):
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
        mock_dt.now.return_value = datetime(2025, 3, 15, 15, 0, tzinfo=IST)
        assert is_entry_window() is True

    @patch("backend.services.price_monitor.datetime")
    def test_window_end_boundary(self, mock_dt):
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
        mock_dt.now.return_value = datetime(2025, 3, 15, 15, 30, tzinfo=IST)
        assert is_entry_window() is True


# ---------------------------------------------------------------------------
# fetch_current_prices (mocked)
# ---------------------------------------------------------------------------

class TestFetchCurrentPrices:
    @patch("backend.services.price_monitor.yf")
    def test_empty_symbols(self, mock_yf):
        result = fetch_current_prices([])
        assert result == {}
        mock_yf.Tickers.assert_not_called()

    @patch("backend.services.price_monitor.yf")
    def test_single_symbol(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 2500.50
        mock_tickers = MagicMock()
        mock_tickers.tickers = {"RELIANCE.NS": mock_ticker}
        mock_yf.Tickers.return_value = mock_tickers

        result = fetch_current_prices(["RELIANCE"])
        assert "RELIANCE" in result
        assert isinstance(result["RELIANCE"], Decimal)

    @patch("backend.services.price_monitor.yf")
    def test_price_zero_excluded(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 0
        mock_tickers = MagicMock()
        mock_tickers.tickers = {"ZERO.NS": mock_ticker}
        mock_yf.Tickers.return_value = mock_tickers

        result = fetch_current_prices(["ZERO"])
        assert "ZERO" not in result

    @patch("backend.services.price_monitor.yf")
    def test_exception_returns_empty(self, mock_yf):
        mock_yf.Tickers.side_effect = Exception("Network error")
        result = fetch_current_prices(["RELIANCE"])
        assert result == {}

    @patch("backend.services.price_monitor.yf")
    def test_ticker_not_found(self, mock_yf):
        mock_tickers = MagicMock()
        mock_tickers.tickers = {}
        mock_yf.Tickers.return_value = mock_tickers

        result = fetch_current_prices(["NONEXISTENT"])
        assert result == {}


# ---------------------------------------------------------------------------
# check_buy_signals
# ---------------------------------------------------------------------------

class TestCheckBuySignals:
    def _make_watchlist_stock(self, symbol, trigger, trp_pct, bucket="READY", status="ACTIVE"):
        stock = MagicMock()
        stock.symbol = symbol
        stock.trigger_level = Decimal(str(trigger))
        stock.planned_sl_pct = trp_pct
        stock.bucket = bucket
        stock.status = status
        stock.id = 1
        return stock

    def _mock_db_with_stocks(self, stocks):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = stocks
        return mock_db

    def test_trigger_break(self):
        stock = self._make_watchlist_stock("RELIANCE", 2500, 3.0)
        db = self._mock_db_with_stocks([stock])
        prices = {"RELIANCE": Decimal("2510")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 1
        assert alerts[0]["alert_category"] == "BUY"
        assert alerts[0]["symbol"] == "RELIANCE"

    def test_price_below_trigger(self):
        stock = self._make_watchlist_stock("RELIANCE", 2500, 3.0)
        db = self._mock_db_with_stocks([stock])
        prices = {"RELIANCE": Decimal("2490")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 0

    def test_trp_below_minimum(self):
        stock = self._make_watchlist_stock("RELIANCE", 2500, 1.5)  # Below min_trp of 2.0
        db = self._mock_db_with_stocks([stock])
        prices = {"RELIANCE": Decimal("2510")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 0

    def test_none_trp_skipped(self):
        stock = self._make_watchlist_stock("RELIANCE", 2500, None)
        db = self._mock_db_with_stocks([stock])
        prices = {"RELIANCE": Decimal("2510")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 0

    def test_no_price_for_symbol(self):
        stock = self._make_watchlist_stock("RELIANCE", 2500, 3.0)
        db = self._mock_db_with_stocks([stock])
        prices = {}  # No prices fetched

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 0

    def test_none_trigger_skipped(self):
        stock = self._make_watchlist_stock("RELIANCE", 2500, 3.0)
        stock.trigger_level = None
        db = self._mock_db_with_stocks([stock])
        prices = {"RELIANCE": Decimal("2510")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 0

    def test_empty_watchlist(self):
        db = self._mock_db_with_stocks([])
        prices = {"RELIANCE": Decimal("2510")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 0

    def test_alert_contains_sizing(self):
        stock = self._make_watchlist_stock("TEST", 500, 3.0)
        db = self._mock_db_with_stocks([stock])
        prices = {"TEST": Decimal("505")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 1
        assert "suggested_qty" in alerts[0]
        assert "suggested_sl_price" in alerts[0]

    def test_exact_trigger_price(self):
        stock = self._make_watchlist_stock("TEST", 500, 3.0)
        db = self._mock_db_with_stocks([stock])
        prices = {"TEST": Decimal("500")}  # Exactly at trigger

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 1

    def test_multiple_stocks(self):
        stocks = [
            self._make_watchlist_stock("A", 100, 3.0),
            self._make_watchlist_stock("B", 200, 3.0),
        ]
        db = self._mock_db_with_stocks(stocks)
        prices = {"A": Decimal("105"), "B": Decimal("190")}

        alerts = check_buy_signals(db, prices, Decimal("500000"), 0.5)
        assert len(alerts) == 1  # Only A breaks trigger
        assert alerts[0]["symbol"] == "A"


# ---------------------------------------------------------------------------
# check_sell_signals
# ---------------------------------------------------------------------------

class TestCheckSellSignals:
    def _make_trade(self, symbol, sl=90, target_2r=120, target_ne=140,
                    target_ge=180, target_ee=220, remaining_qty=100,
                    total_qty=100, status="OPEN"):
        trade = MagicMock()
        trade.symbol = symbol
        trade.sl_price = Decimal(str(sl)) if sl else None
        trade.target_2r = Decimal(str(target_2r)) if target_2r else None
        trade.target_ne = Decimal(str(target_ne)) if target_ne else None
        trade.target_ge = Decimal(str(target_ge)) if target_ge else None
        trade.target_ee = Decimal(str(target_ee)) if target_ee else None
        trade.remaining_qty = remaining_qty
        trade.total_qty = total_qty
        trade.status = status
        trade.id = 1
        return trade

    def _mock_db_with_trades(self, trades):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = trades
        return mock_db

    def test_sl_hit(self):
        trade = self._make_trade("RELIANCE", sl=90)
        db = self._mock_db_with_trades([trade])
        prices = {"RELIANCE": Decimal("85")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "SL_HIT"
        assert alerts[0]["exit_qty"] == 100  # All remaining

    def test_2r_hit(self):
        trade = self._make_trade("RELIANCE", sl=90, target_2r=120)
        db = self._mock_db_with_trades([trade])
        prices = {"RELIANCE": Decimal("125")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "2R_HIT"

    def test_highest_target_wins(self):
        """If price hits GE, only GE alert should fire (not NE or 2R)."""
        trade = self._make_trade("RELIANCE", sl=90, target_2r=120, target_ne=140, target_ge=180)
        db = self._mock_db_with_trades([trade])
        prices = {"RELIANCE": Decimal("185")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "GE_HIT"

    def test_ee_hit(self):
        trade = self._make_trade("RELIANCE", sl=90, target_ee=220)
        db = self._mock_db_with_trades([trade])
        prices = {"RELIANCE": Decimal("225")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "EE_HIT"

    def test_sl_takes_priority_over_targets(self):
        """If somehow SL and targets are misconfigured, SL should win."""
        trade = self._make_trade("X", sl=90, target_2r=85)  # target below SL (edge case)
        db = self._mock_db_with_trades([trade])
        prices = {"X": Decimal("84")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "SL_HIT"

    def test_no_price_for_symbol(self):
        trade = self._make_trade("RELIANCE", sl=90)
        db = self._mock_db_with_trades([trade])
        prices = {}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 0

    def test_zero_remaining_qty(self):
        trade = self._make_trade("RELIANCE", sl=90, remaining_qty=0)
        db = self._mock_db_with_trades([trade])
        prices = {"RELIANCE": Decimal("85")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 0

    def test_none_remaining_qty(self):
        trade = self._make_trade("RELIANCE", sl=90, remaining_qty=None)
        db = self._mock_db_with_trades([trade])
        prices = {"RELIANCE": Decimal("85")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 0

    def test_price_between_sl_and_targets(self):
        """Price is safe, no alerts."""
        trade = self._make_trade("RELIANCE", sl=90, target_2r=120)
        db = self._mock_db_with_trades([trade])
        prices = {"RELIANCE": Decimal("100")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 0

    def test_empty_trades(self):
        db = self._mock_db_with_trades([])
        prices = {"RELIANCE": Decimal("85")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 0

    def test_exit_qty_respects_framework(self):
        """2R exit should be ~20% of total_qty."""
        trade = self._make_trade("TEST", sl=90, target_2r=120, total_qty=100, remaining_qty=100)
        db = self._mock_db_with_trades([trade])
        prices = {"TEST": Decimal("125")}

        alerts = check_sell_signals(db, prices)
        assert len(alerts) == 1
        assert alerts[0]["exit_qty"] == int(100 * TRADING_RULES["mathematical_exit_pct"])


# ---------------------------------------------------------------------------
# _write_check_log
# ---------------------------------------------------------------------------

class TestWriteCheckLog:
    def test_writes_log(self):
        mock_db = MagicMock()
        _write_check_log(mock_db, "MANUAL", "FULL", 10, 8, 2, 1, 500, None)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_with_error(self):
        mock_db = MagicMock()
        _write_check_log(mock_db, "SCHEDULER", "EXITS", 5, 3, 0, 0, 200, "Some error")
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.error_message == "Some error"

    def test_db_failure_swallowed(self):
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("DB error")
        # Should not raise
        _write_check_log(mock_db, "MANUAL", "FULL", 0, 0, 0, 0, 0, None)
