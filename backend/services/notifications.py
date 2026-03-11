"""
Notification service — Telegram bot for real-time alerts and Daily Brief.

Uses python-telegram-bot library for async message sending.
"""

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(text: str) -> bool:
    """
    Send a plain text message via Telegram bot.
    Handles message length limits (4096 chars) by splitting if needed.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id or token == "your_bot_token_here":
        logger.warning("Telegram not configured — message not sent")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Split long messages
    max_len = 4000
    chunks = [text[i : i + max_len] for i in range(0, len(text), max_len)]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for chunk in chunks:
                payload = {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    logger.error(f"Telegram API error: {response.status_code} {response.text}")
                    return False

        logger.info("Telegram message sent successfully")
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


async def send_telegram_alert(alert_type: str, message: str) -> bool:
    """
    Send a formatted alert via Telegram.

    Alert types: SL_HIT, TRIGGER_LEVEL, RISK_WARNING, FREEZE, PPC_DETECTED, etc.
    """
    emoji_map = {
        "SL_HIT": "🔴",
        "TRIGGER_LEVEL": "🟢",
        "RISK_WARNING": "⚠️",
        "FREEZE": "🧊",
        "PPC_DETECTED": "📊",
        "NPC_DETECTED": "📉",
        "ENTRY_SIGNAL": "🎯",
    }
    emoji = emoji_map.get(alert_type, "📌")
    formatted = f"{emoji} <b>{alert_type}</b>\n\n{message}"
    return await send_telegram_message(formatted)


async def send_sl_alert(symbol: str, sl_price: float) -> bool:
    """Send stop-loss hit alert."""
    return await send_telegram_alert(
        "SL_HIT",
        f"Stop loss triggered for <b>{symbol}</b> at ₹{sl_price:.2f}",
    )


async def send_entry_alert(symbol: str, trigger_level: float) -> bool:
    """Send entry trigger alert."""
    return await send_telegram_alert(
        "TRIGGER_LEVEL",
        f"Entry trigger reached for <b>{symbol}</b> at ₹{trigger_level:.2f}",
    )


async def send_daily_brief(brief_text: str) -> bool:
    """Send the CIO Daily Brief via Telegram."""
    return await send_telegram_message(f"<pre>{brief_text}</pre>")
