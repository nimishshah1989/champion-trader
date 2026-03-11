"""
cio_agent.py — Generates the CIO Daily Brief via Claude API.

Runs at 17:00 IST daily.

Inputs gathered before calling Claude:
  1. Today's regime from regime_classifier
  2. Active parameter bank
  3. Overnight AutoOptimize results
  4. Open positions status
  5. Top 3 setups from signal_agent
  6. RAG queries for context
  7. Month-to-date P&L and drawdown

Output: structured Telegram message with setup cards and recommendation.
"""

import json
import logging
from datetime import datetime

from anthropic import Anthropic

from backend.config import settings
from backend.database import SessionLocal, Trade
from backend.intelligence.autooptimize import get_history, get_status as get_optimize_status
from backend.intelligence.parameter_banks import get_active_parameters, get_active_version
from backend.intelligence.portfolio_math import calculate_monthly_pnl, calculate_open_risk
from backend.intelligence.rag_engine import rag_query
from backend.intelligence.regime_classifier import classify_regime, get_latest_regime
from backend.intelligence.signal_agent import get_top_setups

logger = logging.getLogger(__name__)

# Store latest brief for API access
_latest_brief = None


def _format_inr(amount: float) -> str:
    """Format amount in Indian Rupee notation."""
    if abs(amount) >= 1e7:
        return f"₹{amount / 1e7:.2f}Cr"
    elif abs(amount) >= 1e5:
        return f"₹{amount / 1e5:.2f}L"
    else:
        return f"₹{amount:,.0f}"


def _get_open_positions() -> list[dict]:
    """Fetch open trades from database."""
    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(
            Trade.status.in_(["OPEN", "PARTIAL"])
        ).all()
        return [
            {
                "symbol": t.symbol,
                "entry_price": t.avg_entry_price,
                "remaining_qty": t.remaining_qty,
                "stop_loss": t.stop_loss,
                "trp_pct": t.trp_pct,
                "total_pnl": t.total_pnl,
                "status": t.status,
                "entry_date": str(t.entry_date) if t.entry_date else None,
            }
            for t in trades
        ]
    finally:
        db.close()


def _get_closed_trades_this_month() -> list[dict]:
    """Fetch trades closed this month."""
    db = SessionLocal()
    try:
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        trades = db.query(Trade).filter(
            Trade.status.in_(["CLOSED", "STOPPED"]),
            Trade.exit_date >= month_start,
        ).all()
        return [
            {
                "symbol": t.symbol,
                "total_pnl": t.total_pnl,
                "r_multiple": t.r_multiple,
                "exit_date": str(t.exit_date) if t.exit_date else None,
                "status": t.status,
            }
            for t in trades
        ]
    finally:
        db.close()


def _get_overnight_summary() -> str:
    """Summarise overnight AutoOptimize results."""
    history = get_history()
    if not history:
        return "No AutoOptimize experiments run yet."

    # Get experiments from last night
    today = datetime.now().strftime("%Y-%m-%d")
    recent = [h for h in history if h.get("timestamp", "").startswith(today)]

    if not recent:
        # Get last 5 experiments regardless of date
        recent = history[-5:]

    keeps = [h for h in recent if h.get("outcome") == "KEEP"]
    reverts = [h for h in recent if h.get("outcome") == "REVERT"]

    summary = f"{len(recent)} experiments | {len(keeps)} improvements, {len(reverts)} reverted"

    if keeps:
        best = max(keeps, key=lambda x: float(x.get("new_score", 0)) - float(x.get("old_score", 0)))
        delta = float(best.get("new_score", 0)) - float(best.get("old_score", 0))
        summary += f"\nBest: {best.get('parameter')} {best.get('old_value')}→{best.get('new_value')} (+{delta:.4f} score)"

    return summary


async def generate_brief(account_value: float = None) -> dict:
    """
    Generate the CIO Daily Brief.

    Returns dict with brief text and structured data.
    """
    global _latest_brief

    if account_value is None:
        account_value = settings.default_account_value

    logger.info("Generating CIO Daily Brief...")
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Classify regime
    regime_data = await classify_regime()
    regime = regime_data.get("regime", "UNKNOWN")

    # 2. Get active parameter bank
    active_params = get_active_parameters(regime)
    param_version = get_active_version()

    # 3. Overnight results
    overnight = _get_overnight_summary()

    # 4. Open positions
    open_positions = _get_open_positions()
    risk_data = calculate_open_risk(open_positions, account_value)

    # 5. MTD P&L
    closed_trades = _get_closed_trades_this_month()
    mtd = calculate_monthly_pnl(closed_trades)

    # 6. Top setups
    setups = await get_top_setups(
        top_n=3,
        account_value=account_value,
        rpt_pct=settings.default_rpt_pct,
    )

    # 7. RAG context
    rag_context = ""
    if setups:
        top_symbol = setups[0]["symbol"]
        rag_results = rag_query(
            f"Historical performance of {top_symbol} PPC signals in {regime} regime",
            corpus="corpus_c",
            top_k=3,
        )
        if rag_results:
            rag_context = "\n".join(rag_results[:2])

    # Build the brief text
    brief_lines = [
        f"CTS DAILY BRIEF — {today}",
        "═" * 35,
        f"REGIME: {regime} | ADX: {regime_data.get('nifty_adx', '—')} | VIX: {regime_data.get('india_vix', '—')}",
        f"Active Params: {param_version}",
        "",
        f"OVERNIGHT: {overnight}",
        "",
        "PORTFOLIO:",
        f"  Open: {len(open_positions)} positions | Risk: {risk_data['total_risk_pct']:.1f}%",
        f"  MTD P&L: {_format_inr(mtd['mtd_pnl'])} | Trades: {mtd['mtd_trades']} | WR: {mtd['mtd_win_rate']:.0%}",
    ]

    # Position details
    for pos in open_positions[:5]:
        pnl_str = _format_inr(pos.get('total_pnl', 0) or 0)
        brief_lines.append(f"  → {pos['symbol']}: Entry ₹{pos['entry_price']:.0f} | SL ₹{pos['stop_loss']:.0f} | P&L {pnl_str}")

    brief_lines.append("")

    # Setup cards
    if setups:
        brief_lines.append("TODAY'S SETUPS:")
        for i, setup in enumerate(setups, 1):
            brief_lines.extend([
                f"#{i} {setup['symbol']} Score:{setup['composite_score']}/100 Signal:{setup['scan_type']}",
                f"   Entry: ₹{setup['entry_price']:.0f} | Stop: ₹{setup['stop_price']:.0f} | 2R: ₹{setup['target_2r']:.0f}",
                f"   R:R: {setup['rr_ratio']} | Risk: {_format_inr(setup['risk_amount'])} | Base: {setup['base_days']}d {setup['base_quality']}",
            ])
            if rag_context and i == 1:
                # Truncate RAG context for telegram
                ctx_short = rag_context[:150] + "..." if len(rag_context) > 150 else rag_context
                brief_lines.append(f"   RAG: {ctx_short}")
            brief_lines.append("")
    else:
        brief_lines.append("No setups detected today.")
        brief_lines.append("")

    # Generate recommendation via Claude
    recommendation = await _generate_recommendation(
        regime, setups, open_positions, risk_data, mtd
    )
    brief_lines.append(f"CALL: {recommendation}")

    brief_text = "\n".join(brief_lines)

    # Build structured result
    brief_data = {
        "date": today,
        "regime": regime_data,
        "param_version": param_version,
        "overnight_summary": overnight,
        "open_positions": open_positions,
        "risk": risk_data,
        "mtd": mtd,
        "setups": setups,
        "recommendation": recommendation,
        "brief_text": brief_text,
        "generated_at": datetime.now().isoformat(),
    }

    _latest_brief = brief_data

    # Send via Telegram
    try:
        from backend.services.notifications import send_telegram_message
        await send_telegram_message(brief_text)
        logger.info("Daily Brief sent via Telegram")
    except Exception as e:
        logger.error(f"Failed to send brief via Telegram: {e}")

    logger.info("CIO Daily Brief generated successfully")
    return brief_data


async def _generate_recommendation(
    regime: str,
    setups: list[dict],
    positions: list[dict],
    risk_data: dict,
    mtd: dict,
) -> str:
    """Use Claude to generate a one-line trading recommendation."""
    try:
        client = Anthropic(api_key=settings.anthropic_api_key)

        context = {
            "regime": regime,
            "open_positions": len(positions),
            "total_risk_pct": risk_data["total_risk_pct"],
            "mtd_pnl": mtd["mtd_pnl"],
            "mtd_win_rate": mtd["mtd_win_rate"],
            "top_setup_score": setups[0]["composite_score"] if setups else 0,
            "top_setup_symbol": setups[0]["symbol"] if setups else None,
            "risk_exceeds_limit": risk_data["exceeds_limit"],
        }

        response = client.messages.create(
            model=settings.autooptimize_model,
            max_tokens=150,
            system="You are a disciplined swing trading CIO. Give one clear, actionable sentence.",
            messages=[{
                "role": "user",
                "content": f"Given this context, what is today's recommendation?\n{json.dumps(context)}"
            }]
        )

        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        if setups and setups[0]["composite_score"] > 70:
            return f"Consider {setups[0]['symbol']} if market opens constructively."
        return "No compelling setups today. Preserve capital."


def get_latest_brief() -> dict:
    """Return the most recently generated brief."""
    return _latest_brief or {"error": "No brief generated yet"}
