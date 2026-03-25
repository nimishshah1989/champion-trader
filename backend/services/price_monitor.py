"""
Price monitor service -- checks current prices against watchlist triggers and open trade targets.
Generates actionable BUY and SELL alerts persisted in the action_alerts table.

Time-window rules (hardcoded per Champion Trader methodology):
  - EXIT signals (SL, targets): checked any time during market hours (9:15-15:30 IST)
  - ENTRY signals (trigger breaks): ONLY during last 30 minutes (15:00-15:30 IST)

The `check_entries` parameter overrides auto-detection (useful for testing).

Alert generation (buy/sell signal checks) is in price_monitor_alerts.py.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import yfinance as yf
from sqlalchemy.orm import Session

from backend.database import ActionAlert, AutoCheckLog, MarketStanceLog, Trade, Watchlist
from backend.services.price_monitor_alerts import check_buy_signals, check_sell_signals
from backend.services.trading_rules import TRADING_RULES

IST = ZoneInfo("Asia/Kolkata")


def is_entry_window() -> bool:
    """Return True if the current IST time is in the entry window: 15:00-15:30."""
    now = datetime.now(tz=IST)
    minutes_since_midnight = now.hour * 60 + now.minute
    return (15 * 60) <= minutes_since_midnight <= (15 * 60 + 30)

logger = logging.getLogger(__name__)


def fetch_current_prices(symbols: list[str]) -> dict[str, Decimal]:
    """Batch fetch current prices via yfinance. Returns {symbol: Decimal price}."""
    if not symbols:
        return {}

    yf_symbols = [f"{s}.NS" for s in symbols]
    prices: dict[str, Decimal] = {}

    try:
        tickers = yf.Tickers(" ".join(yf_symbols))
        for yf_sym in yf_symbols:
            clean = yf_sym.replace(".NS", "")
            try:
                ticker = tickers.tickers.get(yf_sym)
                if ticker is None:
                    continue
                info = ticker.fast_info
                price = getattr(info, "last_price", None)
                if price and price > 0:
                    prices[clean] = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except Exception as exc:
                logger.warning(f"Failed to get price for {clean}: {exc}")

    except Exception as exc:
        logger.error(f"yfinance batch price fetch failed: {exc}")

    return prices


def run_price_check(
    db: Session,
    account_value: Decimal | None = None,
    rpt_pct: float | None = None,
    check_entries: bool | None = None,
    check_exits: bool = True,
    source: str = "MANUAL",
) -> dict:
    """
    Orchestrator: fetches prices, checks buy & sell signals,
    deduplicates against existing NEW alerts, persists to DB.

    Args:
        check_entries: Whether to generate BUY signals.
                       None = auto-detect from IST time (only True during 15:00-15:30).
                       True/False = explicit override.
        check_exits:   Whether to generate SELL signals. Always True by default.
        source:        "MANUAL" (user triggered) or "SCHEDULER" (automated job).
                       Written to AutoCheckLog for audit trail.
    """
    t_start = time.monotonic()
    error_msg: str | None = None
    new_buy_count = 0
    new_sell_count = 0
    prices_count = 0
    symbols_count = 0

    # Resolve entry window
    if check_entries is None:
        check_entries = is_entry_window()

    # Determine check_type label for audit log
    if check_entries and check_exits:
        check_type = "FULL"
    elif check_entries:
        check_type = "ENTRIES"
    else:
        check_type = "EXITS"

    try:
        # Get defaults from latest market stance if not provided
        if account_value is None or rpt_pct is None:
            latest_stance = (
                db.query(MarketStanceLog)
                .order_by(MarketStanceLog.log_date.desc())
                .first()
            )
            if account_value is None:
                account_value = Decimal("500000")  # Default fallback
            if rpt_pct is None:
                rpt_pct = latest_stance.rpt_pct if latest_stance and latest_stance.rpt_pct else TRADING_RULES["default_rpt_pct"]

        # Collect all symbols we need prices for
        symbols: set[str] = set()

        if check_entries:
            ready_stocks = (
                db.query(Watchlist)
                .filter(Watchlist.bucket == "READY", Watchlist.status == "ACTIVE")
                .all()
            )
            for stock in ready_stocks:
                symbols.add(stock.symbol)

        if check_exits:
            open_trades = db.query(Trade).filter(Trade.status.in_(["OPEN", "PARTIAL"])).all()
            for trade in open_trades:
                symbols.add(trade.symbol)

        if not symbols:
            _write_check_log(
                db, source, check_type, 0, 0, 0, 0,
                int((time.monotonic() - t_start) * 1000), None
            )
            return {
                "buy_alerts": [],
                "sell_alerts": [],
                "last_checked": datetime.now(tz=IST).isoformat(),
                "prices_fetched": 0,
                "check_type": check_type,
                "source": source,
            }

        symbols_count = len(symbols)

        # Fetch prices in one batch
        prices = fetch_current_prices(list(symbols))
        prices_count = len(prices)
        logger.info(
            f"[{source}] Price check ({check_type}): "
            f"fetched {prices_count}/{symbols_count} symbols"
        )

        # Generate alerts
        buy_alert_dicts = check_buy_signals(db, prices, account_value, rpt_pct) if check_entries else []
        sell_alert_dicts = check_sell_signals(db, prices) if check_exits else []

        # Deduplicate -- don't create if a NEW alert already exists for same (symbol, alert_type)
        existing_new = db.query(ActionAlert).filter(ActionAlert.status == "NEW").all()
        existing_keys = {(a.symbol, a.alert_type) for a in existing_new}

        persisted_buy: list[ActionAlert] = []
        for alert_data in buy_alert_dicts:
            key = (alert_data["symbol"], alert_data["alert_type"])
            if key in existing_keys:
                continue
            db_alert = ActionAlert(**alert_data)
            db.add(db_alert)
            db.flush()
            persisted_buy.append(db_alert)
            existing_keys.add(key)
        new_buy_count = len(persisted_buy)

        persisted_sell: list[ActionAlert] = []
        for alert_data in sell_alert_dicts:
            key = (alert_data["symbol"], alert_data["alert_type"])
            if key in existing_keys:
                continue
            db_alert = ActionAlert(**alert_data)
            db.add(db_alert)
            db.flush()
            persisted_sell.append(db_alert)
            existing_keys.add(key)
        new_sell_count = len(persisted_sell)

        db.commit()

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"[{source}] Price check failed: {exc}")
        db.rollback()

    finally:
        duration_ms = int((time.monotonic() - t_start) * 1000)
        _write_check_log(
            db, source, check_type, symbols_count, prices_count,
            new_buy_count, new_sell_count, duration_ms, error_msg
        )

    if error_msg:
        return {
            "buy_alerts": [],
            "sell_alerts": [],
            "last_checked": datetime.now(tz=IST).isoformat(),
            "prices_fetched": 0,
            "check_type": check_type,
            "source": source,
            "error": error_msg,
        }

    # Return all NEW alerts (both freshly created and previously existing)
    all_new = (
        db.query(ActionAlert)
        .filter(ActionAlert.status == "NEW")
        .order_by(ActionAlert.created_at.desc())
        .all()
    )

    buy_results = [a for a in all_new if a.alert_category == "BUY"]
    sell_results = [a for a in all_new if a.alert_category == "SELL"]

    logger.info(
        f"[{source}] Check complete -- {new_buy_count} new BUY, {new_sell_count} new SELL "
        f"({len(buy_results)} total BUY live, {len(sell_results)} total SELL live)"
    )

    return {
        "buy_alerts": buy_results,
        "sell_alerts": sell_results,
        "last_checked": datetime.now(tz=IST).isoformat(),
        "prices_fetched": prices_count,
        "check_type": check_type,
        "source": source,
    }


def _write_check_log(
    db: Session,
    source: str,
    check_type: str,
    symbols_checked: int,
    prices_fetched: int,
    buy_alerts_new: int,
    sell_alerts_new: int,
    duration_ms: int,
    error_message: str | None,
) -> None:
    """Persist an AutoCheckLog row -- fire and forget (never raises)."""
    try:
        log = AutoCheckLog(
            source=source,
            check_type=check_type,
            symbols_checked=symbols_checked,
            prices_fetched=prices_fetched,
            buy_alerts_new=buy_alerts_new,
            sell_alerts_new=sell_alerts_new,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        logger.warning(f"Failed to write AutoCheckLog: {exc}")
