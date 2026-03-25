"""
Price monitor alert generation -- BUY and SELL signal detection.

Checks watchlist stocks for trigger breaks (BUY) and open trades
for SL hits and extension targets (SELL).

Uses Decimal for all financial values per project conventions.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.database import Trade, Watchlist
from backend.services.position_calculator import calculate_position
from backend.services.trading_rules import TRADING_RULES

logger = logging.getLogger(__name__)


def check_buy_signals(
    db: Session,
    prices: dict[str, Decimal],
    account_value: Decimal,
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
                    "rpt_amount": str(sizing["rpt_amount"]),
                    "position_value": str(sizing["position_value"]),
                    "target_2r": str(sizing["target_2r"]),
                    "target_ne": str(sizing["target_ne"]),
                    "target_ge": str(sizing["target_ge"]),
                    "target_ee": str(sizing["target_ee"]),
                }),
            })

    return alerts


def check_sell_signals(
    db: Session,
    prices: dict[str, Decimal],
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
        targets: list[tuple[str, Decimal, int, float, str]] = []
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
