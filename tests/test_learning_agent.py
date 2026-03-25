"""
Tests for backend/intelligence/learning_agent.py

Focuses on pure helper functions:
  _classify_exit_quality, _calculate_hold_days,
  _infer_signal_type, _lookup_regime_at_entry

Run: python -m pytest tests/test_learning_agent.py -v
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import MagicMock, patch

import pytest

from backend.intelligence.learning_agent import (
    _calculate_hold_days,
    _classify_exit_quality,
    _infer_signal_type,
    _lookup_regime_at_entry,
    _update_attribution,
    _check_underperformance,
    process_closed_trades,
    EXIT_R_EXTREME_EXTENSION,
    EXIT_R_GREAT_EXTENSION,
    EXIT_R_NORMAL_EXTENSION,
    EXIT_R_MATHEMATICAL,
    UNDERPERFORMANCE_MIN_TRADES,
    UNDERPERFORMANCE_WIN_RATE_THRESHOLD,
)
from backend.database import ProcessedPostMortem


# ---------------------------------------------------------------------------
# _classify_exit_quality
# ---------------------------------------------------------------------------

class TestClassifyExitQuality:
    def test_extreme_extension(self):
        assert _classify_exit_quality(12.0, "CLOSED") == "EXTREME_EXTENSION"

    def test_extreme_extension_above_threshold(self):
        assert _classify_exit_quality(15.0, "CLOSED") == "EXTREME_EXTENSION"

    def test_great_extension(self):
        assert _classify_exit_quality(8.0, "CLOSED") == "GREAT_EXTENSION"

    def test_great_extension_mid(self):
        assert _classify_exit_quality(10.5, "CLOSED") == "GREAT_EXTENSION"

    def test_normal_extension(self):
        assert _classify_exit_quality(4.0, "CLOSED") == "NORMAL_EXTENSION"

    def test_normal_extension_mid(self):
        assert _classify_exit_quality(6.0, "CLOSED") == "NORMAL_EXTENSION"

    def test_mathematical_exit(self):
        assert _classify_exit_quality(2.0, "CLOSED") == "MATHEMATICAL_EXIT"

    def test_mathematical_exit_mid(self):
        assert _classify_exit_quality(3.5, "CLOSED") == "MATHEMATICAL_EXIT"

    def test_partial_win(self):
        assert _classify_exit_quality(0.5, "CLOSED") == "PARTIAL_WIN"

    def test_partial_win_small(self):
        assert _classify_exit_quality(0.01, "CLOSED") == "PARTIAL_WIN"

    def test_stopped_out(self):
        assert _classify_exit_quality(-1.0, "STOPPED") == "STOPPED_OUT"

    def test_stopped_out_zero(self):
        assert _classify_exit_quality(0, "STOPPED") == "STOPPED_OUT"

    def test_loss(self):
        assert _classify_exit_quality(-0.5, "CLOSED") == "LOSS"

    def test_loss_zero(self):
        assert _classify_exit_quality(0, "CLOSED") == "LOSS"

    def test_loss_none_status(self):
        assert _classify_exit_quality(-1.0, None) == "LOSS"

    def test_decimal_r_multiple(self):
        """Ensure Decimal values work (as they would from DB)."""
        assert _classify_exit_quality(Decimal("8.5"), "CLOSED") == "GREAT_EXTENSION"

    def test_boundary_exact_12(self):
        assert _classify_exit_quality(EXIT_R_EXTREME_EXTENSION, "CLOSED") == "EXTREME_EXTENSION"

    def test_boundary_just_below_12(self):
        assert _classify_exit_quality(11.99, "CLOSED") == "GREAT_EXTENSION"

    def test_boundary_exact_2(self):
        assert _classify_exit_quality(EXIT_R_MATHEMATICAL, "CLOSED") == "MATHEMATICAL_EXIT"


# ---------------------------------------------------------------------------
# _calculate_hold_days
# ---------------------------------------------------------------------------

class TestCalculateHoldDays:
    def test_same_day(self):
        d = date(2025, 1, 15)
        assert _calculate_hold_days(d, d) == 0

    def test_one_day(self):
        assert _calculate_hold_days(date(2025, 1, 15), date(2025, 1, 16)) == 1

    def test_multi_day(self):
        assert _calculate_hold_days(date(2025, 1, 1), date(2025, 1, 31)) == 30

    def test_cross_month(self):
        assert _calculate_hold_days(date(2025, 1, 28), date(2025, 2, 3)) == 6

    def test_none_entry(self):
        assert _calculate_hold_days(None, date(2025, 1, 15)) == 0

    def test_none_exit(self):
        assert _calculate_hold_days(date(2025, 1, 15), None) == 0

    def test_both_none(self):
        assert _calculate_hold_days(None, None) == 0

    def test_string_dates(self):
        """DB may store dates as strings."""
        assert _calculate_hold_days("2025-01-01", "2025-01-10") == 9

    def test_mixed_types(self):
        assert _calculate_hold_days(date(2025, 1, 1), "2025-01-10") == 9

    def test_invalid_string(self):
        assert _calculate_hold_days("not-a-date", date(2025, 1, 1)) == 0


# ---------------------------------------------------------------------------
# _infer_signal_type
# ---------------------------------------------------------------------------

class TestInferSignalType:
    def _make_trade(self, setup_type=None, entry_notes=None):
        trade = MagicMock()
        trade.setup_type = setup_type
        trade.entry_notes = entry_notes
        return trade

    def test_ppc_from_setup_type(self):
        assert _infer_signal_type(self._make_trade(setup_type="PPC")) == "PPC"

    def test_npc_from_setup_type(self):
        assert _infer_signal_type(self._make_trade(setup_type="NPC")) == "NPC"

    def test_contraction_from_setup_type(self):
        assert _infer_signal_type(self._make_trade(setup_type="CONTRACTION")) == "CONTRACTION"

    def test_ppc_from_setup_type_lowercase(self):
        assert _infer_signal_type(self._make_trade(setup_type="ppc_scan")) == "PPC"

    def test_npc_from_notes(self):
        assert _infer_signal_type(self._make_trade(entry_notes="NPC scan detected")) == "NPC"

    def test_contraction_from_notes(self):
        assert _infer_signal_type(self._make_trade(entry_notes="contraction squeeze")) == "CONTRACTION"

    def test_default_fallback(self):
        assert _infer_signal_type(self._make_trade()) == "PPC"

    def test_none_values(self):
        assert _infer_signal_type(self._make_trade(setup_type=None, entry_notes=None)) == "PPC"

    def test_empty_strings(self):
        assert _infer_signal_type(self._make_trade(setup_type="", entry_notes="")) == "PPC"

    def test_setup_type_priority_over_notes(self):
        """setup_type NPC should win even if notes mention CONTRACTION."""
        assert _infer_signal_type(self._make_trade(setup_type="NPC_SCAN", entry_notes="contraction")) == "NPC"

    def test_auto_paper_setup(self):
        """AUTO_PAPER has no signal keyword, defaults to PPC."""
        assert _infer_signal_type(self._make_trade(setup_type="AUTO_PAPER")) == "PPC"


# ---------------------------------------------------------------------------
# _lookup_regime_at_entry
# ---------------------------------------------------------------------------

class TestLookupRegimeAtEntry:
    def test_regime_found(self):
        mock_db = MagicMock()
        mock_regime = MagicMock()
        mock_regime.regime = "BULLISH"
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_regime

        result = _lookup_regime_at_entry(mock_db, date(2025, 3, 1))
        assert result == "BULLISH"

    def test_no_regime_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        result = _lookup_regime_at_entry(mock_db, date(2025, 3, 1))
        assert result == "UNKNOWN"

    def test_none_entry_date(self):
        mock_db = MagicMock()
        assert _lookup_regime_at_entry(mock_db, None) == "UNKNOWN"

    def test_db_exception(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB error")
        assert _lookup_regime_at_entry(mock_db, date(2025, 3, 1)) == "UNKNOWN"


# ---------------------------------------------------------------------------
# _update_attribution
# ---------------------------------------------------------------------------

class TestUpdateAttribution:
    def test_new_attribution_win(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        _update_attribution(mock_db, "PPC", "BULLISH", 2.5)
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.signal_type == "PPC"
        assert added.regime == "BULLISH"
        assert added.trade_count == 1
        assert added.win_count == 1

    def test_new_attribution_loss(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        _update_attribution(mock_db, "NPC", "BEARISH", -1.0)
        added = mock_db.add.call_args[0][0]
        assert added.win_count == 0

    def test_existing_attribution_update(self):
        mock_db = MagicMock()
        existing = MagicMock()
        existing.trade_count = 10
        existing.win_count = 6
        existing.total_r = 15.0
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        _update_attribution(mock_db, "PPC", "BULLISH", 2.0)
        assert existing.trade_count == 11
        assert existing.win_count == 7
        assert existing.total_r == 17.0


# ---------------------------------------------------------------------------
# _check_underperformance
# ---------------------------------------------------------------------------

class TestCheckUnderperformance:
    def test_underperforming_logs_warning(self):
        mock_db = MagicMock()
        attr = MagicMock()
        attr.trade_count = 25
        attr.win_rate = 0.30
        mock_db.query.return_value.filter.return_value.first.return_value = attr

        with patch("backend.intelligence.learning_agent.logger") as mock_logger:
            _check_underperformance(mock_db, "PPC", "BEARISH")
            mock_logger.warning.assert_called_once()

    def test_not_enough_trades(self):
        mock_db = MagicMock()
        attr = MagicMock()
        attr.trade_count = 5
        attr.win_rate = 0.20
        mock_db.query.return_value.filter.return_value.first.return_value = attr

        with patch("backend.intelligence.learning_agent.logger") as mock_logger:
            _check_underperformance(mock_db, "PPC", "BEARISH")
            mock_logger.warning.assert_not_called()

    def test_good_win_rate(self):
        mock_db = MagicMock()
        attr = MagicMock()
        attr.trade_count = 30
        attr.win_rate = 0.55
        mock_db.query.return_value.filter.return_value.first.return_value = attr

        with patch("backend.intelligence.learning_agent.logger") as mock_logger:
            _check_underperformance(mock_db, "PPC", "BULLISH")
            mock_logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# process_closed_trades — DB persistence of processed IDs
# ---------------------------------------------------------------------------

class TestProcessClosedTradesPersistence:
    """Verify _processed_trade_ids replaced by ProcessedPostMortem table."""

    @pytest.mark.asyncio
    async def test_skips_already_processed_trades(self):
        """Trades already in ProcessedPostMortem are not re-processed."""
        mock_trade = MagicMock()
        mock_trade.id = 42
        mock_trade.status = "CLOSED"

        mock_already = MagicMock()
        mock_already.trade_id = 42

        with patch("backend.intelligence.learning_agent.SessionLocal") as MockSession:
            db = MagicMock()
            MockSession.return_value = db

            # First query: ProcessedPostMortem.trade_id → returns {42}
            # Second query: Trade → returns [mock_trade]
            def query_side_effect(model):
                q = MagicMock()
                if model is ProcessedPostMortem.trade_id:
                    q.all.return_value = [mock_already]
                else:
                    q.filter.return_value.all.return_value = [mock_trade]
                return q
            db.query.side_effect = query_side_effect

            await process_closed_trades()

            # Should NOT call db.add because trade 42 is already processed
            db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_processes_new_trade_and_persists(self):
        """New closed trade gets post-mortem'd and recorded in DB."""
        mock_trade = MagicMock()
        mock_trade.id = 99
        mock_trade.status = "CLOSED"
        mock_trade.symbol = "RELIANCE"
        mock_trade.avg_entry_price = 2500
        mock_trade.exit_price = 2600
        mock_trade.trp_at_entry = 3.0
        mock_trade.r_multiple = 2.0
        mock_trade.gross_pnl = 10000
        mock_trade.entry_date = date(2026, 1, 1)
        mock_trade.exit_date = date(2026, 1, 15)
        mock_trade.sl_price = 2425
        mock_trade.setup_type = "PPC"
        mock_trade.entry_notes = ""

        with patch("backend.intelligence.learning_agent.SessionLocal") as MockSession, \
             patch("backend.intelligence.learning_agent.ingest_document"), \
             patch("backend.intelligence.learning_agent._generate_post_mortem") as mock_pm:
            db = MagicMock()
            MockSession.return_value = db

            # First query returns no processed IDs, second returns closed trades
            query_results = MagicMock()
            # db.query(ProcessedPostMortem.trade_id).all() → empty
            first_query = MagicMock()
            first_query.all.return_value = []
            # db.query(Trade).filter(...).all() → [mock_trade]
            second_query = MagicMock()
            second_query.filter.return_value.all.return_value = [mock_trade]

            db.query.side_effect = [first_query, second_query]

            await process_closed_trades()

            # _generate_post_mortem should have been called
            mock_pm.assert_called_once_with(db, mock_trade)

            # Should have called db.add with a ProcessedPostMortem record
            add_calls = db.add.call_args_list
            pm_added = [
                c for c in add_calls
                if isinstance(c[0][0], ProcessedPostMortem)
            ]
            assert len(pm_added) == 1
            assert pm_added[0][0][0].trade_id == 99

    def test_processed_post_mortem_table_exists(self):
        """Verify the ProcessedPostMortem model is properly defined."""
        assert ProcessedPostMortem.__tablename__ == "processed_post_mortems"
        assert hasattr(ProcessedPostMortem, "trade_id")
        assert hasattr(ProcessedPostMortem, "processed_at")
