"""
Notification service — Telegram bot for real-time alerts.
TODO: Implement in Phase 5.
"""

from backend.config import settings


async def send_telegram_alert(message: str) -> bool:
    """
    Send a message via Telegram bot.

    TODO: implement using python-telegram-bot library.
    Uses settings.telegram_bot_token and settings.telegram_chat_id.
    """
    raise NotImplementedError("Telegram notifications not yet implemented")


async def send_sl_alert(symbol: str, sl_price: float) -> bool:
    """Send stop-loss hit alert. TODO: implement."""
    raise NotImplementedError("SL alert not yet implemented")


async def send_entry_alert(symbol: str, trigger_level: float) -> bool:
    """Send entry trigger alert. TODO: implement."""
    raise NotImplementedError("Entry alert not yet implemented")
