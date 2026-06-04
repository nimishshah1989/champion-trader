"""
Kite morning alert — sends the daily login link to Telegram at 08:45 IST.

The user taps the link, logs in to Zerodha on their phone, and the backend
auto-captures the access token via GET /kite/callback.
"""
from __future__ import annotations

import logging

from backend.config import settings
from backend.engine.kite_data import login_url
from backend.services.notifications import send_telegram_message

logger = logging.getLogger(__name__)


async def send_kite_login_alert() -> None:
    """Send the Kite authorization link via Telegram."""
    if not settings.kite_api_key:
        logger.warning("[Kite Morning] KITE_API_KEY not set — skipping alert")
        return

    url = login_url(settings.kite_api_key)

    msg = (
        "🌅 <b>Good morning!</b> Kite authorization needed.\n\n"
        "Tap the link below, log in to Zerodha (takes ~10 seconds), "
        "and your credentials will be updated automatically:\n\n"
        f'<a href="{url}">🔑 Authorize Kite for today</a>\n\n'
        "Once done you'll get a confirmation here."
    )

    await send_telegram_message(msg)
    logger.info("[Kite Morning] Login alert sent via Telegram")
