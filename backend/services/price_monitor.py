"""
Price monitor service — checks current prices against watchlist triggers and open trade targets.
Generates actionable BUY and SELL alerts persisted in the action_alerts table.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import yfinance as yf
from sqlalchemy.orm import Session

from backend.database import ActionAlert, MarketStanceLog, Trade, Watchlist
from backend.services.position_calculator import calculate_position
from backend.services.trading_rules import TRADING_RULES

logger = logging.getLogger(__name__)


def fetch_current_prices(symbols: list[str]) -> dict[str, float]:
    """Batch fetch current prices via yfinance. Returns {symbol: price}."""
    if not symbols:
        return {}

    yf_symbols = [f"{s}.NS" for s in symbols]
    prices: dict[str, float] = {}

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
                    prices[clean] = round(float(price), 2)
            except Exception as exc:
                logger.warning(f"Failed to get price for {clean}: {exc}")

    except Exception as exc:
        logger.error(f"yfinance batch price fetch failed: {exc}")

    return prices


def check_buy_signals(
    db: Session,
    prices: dict[str, float],
    account_value: float,
    rpt_pct: float,
) -> list[dict]:
    """
    Check READY watchlist stocks for trigger breaks.
    Returns list of alert dicts ready to persist.
    """
    alerts: list[dict] = []

    # Get READY watchlist items with trigger levels
    ready_stocks = (
        db.query(Watchlist)
        .filter(
            Watchlist.bucket == "READY",
            Watchlist.status == "ACTIVE",
            Watchlist.trigger_level.isnot(None),
        )
        .all()
    )

    for stock in ready_stocks:
        current_price = prices.get(stock.symbol)
        if current_price is None:
            continue

        trigger = stock.trigger_level
        if trigger is None:
            continue

        # Signal: current price >= trigger level
        if current_price >= trigger:
            # Use planned_sl_pct (TRP) if available, otherwise estimate from trigger
            trp_pct = stock.planned_sl_pct
            if trp_pct is None or trp_pct < TRADING_RULES["min_trp"]:
                continue

            # Calculate position sizing using trigger as entry price
            sizing = calculate_position(account_value, rpt_pct, trigger, trp_pct)

            action_text = (
                f"BUY {stock.symbol}: Price ₹{current_price:.2f} broke trigger ₹{trigger:.2f}. "
                f"Enter {sizing['position_size']} qty (half={sizing['half_qty']}) at ₹{trigger:.2f}, "
                f"SL ₹{sizing['sl_price']:.2f}"
            )

            alerts.append({
                "alert_category": "BUY",
                "alert_type": "TRIGGER_BREAK",
                "symbol": stock.symbol,
                "current_price": current_price,
                "trigger_price": trigger,
                "suggested_qty": sizing["position_size"],
                "suggested_half_qty": sizing["half_qty"],
                "suggested_sl_price": sizing["sl_price"],
                "suggested_entry_price": trigger,
                "account_value_used": account_value,
                "rpt_pct_used": rpt_pct,
                "trp_pct": trp_pct,
                "action_text": action_text,
                "source": "PRICE_CHECK",
                "watchlist_id": stock.id,
                "data": json.dumps({
                    "rpt_amount": sizing["rpt_amount"],
                    "position_value": sizing["position_value"],
                    "target_2r": sizing["target_2r"],
                    "target_ne": sizing["target_ne"],
                    "target_ge": sizing["target_ge"],
                    "target_ee": sizing["target_ee"],
                }),
            })

    return alerts


def check_sell_signals(
    db: Session,
    prices: dict[str, float],
) -> list[dict]:
    """
    Check open/partial trades against SL and extension targets.
    Priority: SL first (exit all), then highest applicable target only (EE > GE > NE > 2R).
    Exit qty follows framework: 2R=20%, NE=20%, GE=40%, EE=80% of original total_qty.
    """
    alerts: list[dict] = []

    open_trades = (
        db.query(Trade)
        .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
        .all()
    )

    for trade in open_trades:
        current_price = prices.get(trade.symbol)
        if current_price is None:
            continue

        if trade.remaining_qty is None or trade.remaining_qty <= 0:
            continue

        total_qty = trade.total_qty or trade.remaining_qty

        # SL check first — exit ALL remaining
        if trade.sl_price and current_price <= trade.sl_price:
            action_text = (
                f"SL HIT {trade.symbol}: Price ₹{current_price:.2f} ≤ SL ₹{trade.sl_price:.2f}. "
                f"EXIT ALL {trade.remaining_qty} shares."
            )
            alerts.append({
                "alert_category": "SELL",
                "alert_type": "SL_HIT",
                "symbol": trade.symbol,
                "current_price": current_price,
                "trigger_price": trade.sl_price,
                "trade_id": trade.id,
                "exit_qty": trade.remaining_qty,
                "exit_pct": 100.0,
                "target_level": trade.sl_price,
                "remaining_qty_after": 0,
                "action_text": action_text,
                "source": "PRICE_CHECK",
            })
            continue  # SL takes priority, skip target checks

        # Check targets from highest down — only generate alert for the highest applicable
        targets = []
        if trade.target_ee and current_price >= trade.target_ee:
            exit_qty = min(int(total_qty * TRADING_RULES["ee_exit_pct"]), trade.remaining_qty)
            targets.append(("EE_HIT", trade.target_ee, exit_qty, TRADING_RULES["ee_exit_pct"] * 100, "Extreme Extension"))
        elif trade.target_ge and current_price >= trade.target_ge:
            exit_qty = min(int(total_qty * TRADING_RULES["ge_exit_pct"]), trade.remaining_qty)
            targets.append(("GE_HIT", trade.target_ge, exit_qty, TRADING_RULES["ge_exit_pct"] * 100, "Great Extension"))
        elif trade.target_ne and current_price >= trade.target_ne:
            exit_qty = min(int(total_qty * TRADING_RULES["ne_exit_pct"]), trade.remaining_qty)
            targets.append(("NE_HIT", trade.target_ne, exit_qty, TRADING_RULES["ne_exit_pct"] * 100, "Normal Extension"))
        elif trade.target_2r and current_price >= trade.target_2r:
            exit_qty = min(int(total_qty * TRADING_RULES["mathematical_exit_pct"]), trade.remaining_qty)
            targets.append(("2R_HIT", trade.target_2r, exit_qty, TRADING_RULES["mathematical_exit_pct"] * 100, "2R Mathematical"))

        for alert_type, target_price, exit_qty, exit_pct, label in targets:
            if exit_qty <= 0:
                continue
            remaining_after = trade.remaining_qty - exit_qty
            action_text = (
                f"{label} {trade.symbol}: Price ₹{current_price:.2f} ≥ Target ₹{target_price:.2f}. "
                f"EXIT {exit_qty} shares ({exit_pct:.0f}% of original). "
                f"Remaining: {remaining_after}"
            )
            alerts.append({
                "alert_category": "SELL",
                "alert_type": alert_type,
                "symbol": trade.symbol,
                "current_price": current_price,
                "trigger_price": target_price,
                "trade_id": trade.id,
                "exit_qty": exit_qty,
                "exit_pct": exit_pct,
                "target_level": target_price,
                "remaining_qty_after": remaining_after,
                "action_text": action_text,
                "source": "PRICE_CHECK",
            })

    return alerts


def run_price_check(
    db: Session,
    account_value: float | None = None,
    rpt_pct: float | None = None,
) -> dict:
    """
    Orchestrator: fetches prices, checks buy & sell signals,
    deduplicates against existing NEW alerts, persists to DB.
    """
    # Get defaults from latest market stance if not provided
    if account_value is None or rpt_pct is None:
        latest_stance = (
            db.query(MarketStanceLog)
            .order_by(MarketStanceLog.log_date.desc())
            .first()
        )
        if account_value is None:
            account_value = 500000.0  # Default fallback
        if rpt_pct is None:
            rpt_pct = latest_stance.rpt_pct if latest_stance and latest_stance.rpt_pct else TRADING_RULES["default_rpt_pct"]

    # Collect all symbols we need prices for
    symbols: set[str] = set()

    # Watchlist READY symbols
    ready_stocks = (
        db.query(Watchlist)
        .filter(Watchlist.bucket == "READY", Watchlist.status == "ACTIVE")
        .all()
    )
    for stock in ready_stocks:
        symbols.add(stock.symbol)

    # Open trade symbols
    open_trades = db.query(Trade).filter(Trade.status.in_(["OPEN", "PARTIAL"])).all()
    for trade in open_trades:
        symbols.add(trade.symbol)

    if not symbols:
        return {
            "buy_alerts": [],
            "sell_alerts": [],
            "last_checked": datetime.now().isoformat(),
            "prices_fetched": 0,
        }

    # Fetch prices in one batch
    prices = fetch_current_prices(list(symbols))
    logger.info(f"Fetched prices for {len(prices)}/{len(symbols)} symbols")

    # Generate alerts
    buy_alerts = check_buy_signals(db, prices, account_value, rpt_pct)
    sell_alerts = check_sell_signals(db, prices)

    # Deduplicate — don't create if a NEW alert already exists for same (symbol, alert_type)
    existing_new = (
        db.query(ActionAlert)
        .filter(ActionAlert.status == "NEW")
        .all()
    )
    existing_keys = {(a.symbol, a.alert_type) for a in existing_new}

    persisted_buy: list[ActionAlert] = []
    for alert_data in buy_alerts:
        key = (alert_data["symbol"], alert_data["alert_type"])
        if key in existing_keys:
            continue
        db_alert = ActionAlert(**alert_data)
        db.add(db_alert)
        db.flush()
        persisted_buy.append(db_alert)
        existing_keys.add(key)

    persisted_sell: list[ActionAlert] = []
    for alert_data in sell_alerts:
        key = (alert_data["symbol"], alert_data["alert_type"])
        if key in existing_keys:
            continue
        db_alert = ActionAlert(**alert_data)
        db.add(db_alert)
        db.flush()
        persisted_sell.append(db_alert)
        existing_keys.add(key)

    db.commit()

    # Return all NEW alerts (both freshly created and previously existing)
    all_new = (
        db.query(ActionAlert)
        .filter(ActionAlert.status == "NEW")
        .order_by(ActionAlert.created_at.desc())
        .all()
    )

    buy_results = [a for a in all_new if a.alert_category == "BUY"]
    sell_results = [a for a in all_new if a.alert_category == "SELL"]

    return {
        "buy_alerts": buy_results,
        "sell_alerts": sell_results,
        "last_checked": datetime.now().isoformat(),
        "prices_fetched": len(prices),
    }
