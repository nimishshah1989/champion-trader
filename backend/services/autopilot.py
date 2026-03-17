"""autopilot.py -- Fully automated virtual paper trading engine.

Closes 3 pipeline gaps: scan→watchlist, BUY alert→trade, SELL alert→exit.
All trades use virtual capital. No real money. No broker calls.
"""
from __future__ import annotations

import json
import logging
from datetime import date as date_type, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.database import (
    ActionAlert, ScanResult, ShadowTrade, Trade, Watchlist, SessionLocal,
)
from backend.intelligence.regime_classifier import get_latest_regime
from backend.services.position_calculator import calculate_position

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

# Risk guardrails — hardcoded, never overridden
VIRTUAL_CAPITAL = Decimal("100000")       # ₹1,00,000
RPT_PCT = 0.50                            # 0.5% risk per trade
MAX_OPEN_RISK_PCT = Decimal("10.0")       # 10% of capital = ₹10,000
MAX_POSITIONS = 5                         # max simultaneous open trades
MIN_TRP = Decimal("2.0")                  # minimum TRP to be tradeable


# ---------------------------------------------------------------------------
# Gap A: Post-scan → auto-populate watchlist
# ---------------------------------------------------------------------------

def post_scan_populate(db: Session) -> int:
    """
    Read today's scan results, auto-add qualifying stocks to watchlist.
    Only adds stocks not already on the active watchlist.
    Returns count of new watchlist entries.
    """
    today = date_type.today()

    # Get today's scan results
    results = (
        db.query(ScanResult)
        .filter(ScanResult.scan_date == today)
        .all()
    )

    if not results:
        logger.info("[AUTOPILOT] No scan results for today — nothing to populate")
        return 0

    # Get existing active watchlist symbols
    existing_symbols = {
        w.symbol
        for w in db.query(Watchlist)
        .filter(Watchlist.status == "ACTIVE")
        .all()
    }

    # Get open trade symbols — don't add stocks we already hold
    open_trade_symbols = {
        t.symbol
        for t in db.query(Trade)
        .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
        .all()
    }

    added = 0
    for scan in results:
        # Skip if already on watchlist or already in a trade
        if scan.symbol in existing_symbols or scan.symbol in open_trade_symbols:
            continue

        # Only add READY and NEAR stocks
        bucket = scan.watchlist_bucket
        if bucket not in ("READY", "NEAR"):
            continue

        # Must pass liquidity filter
        if not scan.passes_liquidity_filter:
            continue

        # TRP must be above minimum
        trp_val = float(scan.trp) if scan.trp else 0
        if trp_val < float(MIN_TRP):
            continue

        # Create watchlist entry
        entry = Watchlist(
            symbol=scan.symbol,
            added_date=today,
            bucket=bucket,
            stage=scan.stage,
            base_days=scan.base_days,
            base_quality=scan.base_quality,
            wuc_types=scan.wuc_type,
            trigger_level=scan.trigger_level,
            planned_entry_price=scan.trigger_level,
            planned_sl_pct=trp_val,
            status="ACTIVE",
            notes=f"Auto-added from {scan.scan_type} scan on {today}",
        )
        db.add(entry)
        existing_symbols.add(scan.symbol)
        added += 1

    if added > 0:
        db.commit()
        logger.info(
            f"[AUTOPILOT] Auto-populated {added} stocks to watchlist from today's scan"
        )
    else:
        logger.info("[AUTOPILOT] No new qualifying stocks to add to watchlist")

    return added


# ---------------------------------------------------------------------------
# Gap B: BUY alert → auto-execute trade
# ---------------------------------------------------------------------------

def auto_execute_buys(db: Session) -> int:
    """
    Find all NEW BUY alerts and auto-execute them as virtual trades.
    Respects all risk guardrails.
    Returns count of trades opened.
    """
    # Check guardrails first
    open_trades = (
        db.query(Trade)
        .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
        .all()
    )

    if len(open_trades) >= MAX_POSITIONS:
        logger.info(
            f"[AUTOPILOT] Max positions ({MAX_POSITIONS}) reached — skipping buys"
        )
        return 0

    # Calculate current open risk
    current_risk = sum(
        Decimal(str(t.rpt_amount or 0)) for t in open_trades
    )
    max_risk = VIRTUAL_CAPITAL * MAX_OPEN_RISK_PCT / Decimal("100")

    if current_risk >= max_risk:
        logger.info(
            f"[AUTOPILOT] Max open risk ₹{max_risk} reached "
            f"(current: ₹{current_risk}) — skipping buys"
        )
        return 0

    # Get NEW BUY alerts
    buy_alerts = (
        db.query(ActionAlert)
        .filter(
            ActionAlert.alert_category == "BUY",
            ActionAlert.status == "NEW",
        )
        .order_by(ActionAlert.created_at.asc())
        .all()
    )

    if not buy_alerts:
        return 0

    executed = 0
    for alert in buy_alerts:
        # Re-check position limit
        if len(open_trades) + executed >= MAX_POSITIONS:
            break

        # Re-check risk limit
        remaining_risk = max_risk - current_risk
        if remaining_risk <= 0:
            break

        # Validate TRP
        trp_pct = alert.trp_pct
        if not trp_pct or trp_pct < float(MIN_TRP):
            logger.warning(
                f"[AUTOPILOT] Skipping {alert.symbol}: TRP {trp_pct}% below minimum {MIN_TRP}%"
            )
            alert.status = "DISMISSED"
            alert.acted_at = datetime.now(tz=IST)
            continue

        # Calculate position sizing with virtual capital
        entry_price = alert.suggested_entry_price or alert.trigger_price
        if not entry_price:
            continue

        sizing = calculate_position(
            VIRTUAL_CAPITAL, RPT_PCT, entry_price, trp_pct
        )

        rpt_amount = Decimal(str(sizing["rpt_amount"]))

        # Check if this trade would breach risk limit
        if current_risk + rpt_amount > max_risk:
            logger.info(
                f"[AUTOPILOT] Skipping {alert.symbol}: "
                f"would breach max risk (current ₹{current_risk} + ₹{rpt_amount} > ₹{max_risk})"
            )
            continue

        # Create the trade
        trade = Trade(
            symbol=alert.symbol,
            entry_date=date_type.today(),
            entry_type="LIVE_BREAK",
            entry_price_half1=entry_price,
            qty_half1=sizing["half_qty"],
            total_qty=sizing["position_size"],
            avg_entry_price=entry_price,
            trp_at_entry=Decimal(str(trp_pct)),
            sl_price=sizing["sl_price"],
            sl_pct=trp_pct,
            rpt_amount=rpt_amount,
            target_2r=sizing["target_2r"],
            target_ne=sizing["target_ne"],
            target_ge=sizing["target_ge"],
            target_ee=sizing["target_ee"],
            status="OPEN",
            remaining_qty=sizing["position_size"],
            setup_type="AUTO_PAPER",
            entry_notes=(
                f"Auto-executed by autopilot. "
                f"Virtual capital ₹{VIRTUAL_CAPITAL}. RPT {RPT_PCT}%."
            ),
        )
        db.add(trade)
        db.flush()  # Get trade.id

        # Mark alert as acted
        alert.status = "ACTED"
        alert.acted_at = datetime.now(tz=IST)
        alert.resulting_trade_id = trade.id

        # Also create a shadow trade for comparison tracking
        try:
            regime_data = get_latest_regime()
            regime = regime_data.get("regime", "UNKNOWN")
        except Exception:
            regime = "UNKNOWN"

        shadow = ShadowTrade(
            signal_date=date_type.today(),
            symbol=alert.symbol,
            signal_type="PPC",
            composite_score=0,
            entry_price=entry_price,
            stop_price=sizing["sl_price"],
            target_price=sizing["target_2r"],
            rr_ratio=2.0,
            regime=regime,
            was_approved=True,  # auto-approved
        )
        db.add(shadow)

        current_risk += rpt_amount
        executed += 1

        logger.info(
            f"[AUTOPILOT] Trade opened: {alert.symbol} "
            f"qty={sizing['position_size']} entry=₹{entry_price} "
            f"SL=₹{sizing['sl_price']} risk=₹{rpt_amount}"
        )

    if executed > 0:
        db.commit()
        logger.info(f"[AUTOPILOT] Auto-executed {executed} BUY trades")

    return executed


# ---------------------------------------------------------------------------
# Gap C: SELL alert → auto-execute exit
# ---------------------------------------------------------------------------

def auto_execute_sells(db: Session) -> int:
    """
    Find all NEW SELL alerts and auto-execute exits.
    SL hits exit ALL remaining. Target hits exit per framework.
    Returns count of exits executed.
    """
    sell_alerts = (
        db.query(ActionAlert)
        .filter(
            ActionAlert.alert_category == "SELL",
            ActionAlert.status == "NEW",
        )
        .order_by(ActionAlert.created_at.asc())
        .all()
    )

    if not sell_alerts:
        return 0

    executed = 0
    for alert in sell_alerts:
        if not alert.trade_id:
            continue

        trade = db.query(Trade).filter(Trade.id == alert.trade_id).first()
        if not trade or trade.status not in ("OPEN", "PARTIAL"):
            alert.status = "DISMISSED"
            alert.acted_at = datetime.now(tz=IST)
            continue

        exit_qty = alert.exit_qty or trade.remaining_qty
        exit_price = alert.trigger_price or alert.current_price

        if not exit_qty or exit_qty <= 0 or not exit_price:
            continue

        # Calculate P&L for this exit
        entry_price = trade.avg_entry_price or Decimal("0")
        pnl_per_share = exit_price - entry_price
        gross_pnl = pnl_per_share * exit_qty

        # Update trade
        new_remaining = (trade.remaining_qty or 0) - exit_qty
        trade.remaining_qty = max(new_remaining, 0)

        if trade.remaining_qty <= 0:
            trade.status = "CLOSED"
            trade.exit_date = date_type.today()
            trade.exit_price = exit_price
            trade.exit_method = alert.alert_type
            trade.gross_pnl = gross_pnl
            # Calculate R-multiple
            risk = entry_price - (trade.sl_price or entry_price)
            if risk > 0:
                trade.r_multiple = float(pnl_per_share / risk)
                trade.pnl_pct = float(pnl_per_share / entry_price * 100)
        else:
            trade.status = "PARTIAL"

        # Mark alert as acted
        alert.status = "ACTED"
        alert.acted_at = datetime.now(tz=IST)

        executed += 1
        exit_label = alert.alert_type or "EXIT"
        logger.info(
            f"[AUTOPILOT] Exit executed: {trade.symbol} "
            f"{exit_label} qty={exit_qty} @ ₹{exit_price} "
            f"P&L=₹{gross_pnl:.2f} remaining={trade.remaining_qty}"
        )

    if executed > 0:
        db.commit()
        logger.info(f"[AUTOPILOT] Auto-executed {executed} SELL exits")

    return executed


# ---------------------------------------------------------------------------
# Orchestrator — called by scheduler after relevant events
# ---------------------------------------------------------------------------

def run_post_scan_automation() -> dict:
    """Called after daily scanner. Populates watchlist from scan results."""
    db = SessionLocal()
    try:
        added = post_scan_populate(db)
        return {"watchlist_added": added}
    except Exception as exc:
        logger.error(f"[AUTOPILOT] Post-scan automation failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()


def run_post_alert_automation() -> dict:
    """Called after price checks. Auto-executes any NEW alerts."""
    db = SessionLocal()
    try:
        buys = auto_execute_buys(db)
        sells = auto_execute_sells(db)
        return {"buys_executed": buys, "sells_executed": sells}
    except Exception as exc:
        logger.error(f"[AUTOPILOT] Post-alert automation failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()


# Portfolio summary lives in autopilot_report.py (400-line limit split)
