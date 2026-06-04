"""
Kite OAuth callback + daily token refresh.

Flow:
  1. 08:45 IST — scheduler sends Telegram message with the Kite login URL.
  2. User taps the link on their phone → logs in to Zerodha.
  3. Zerodha redirects to GET /kite/callback?request_token=XXX&status=success
  4. This endpoint exchanges the request_token for an access_token, saves it
     to .env, updates settings in memory, and sends a Telegram confirmation.

One-time Kite developer console setup required:
  Set your app's redirect URL to: <your-backend-url>/kite/callback
"""
from __future__ import annotations

import logging
import os
import re

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from backend.config import settings
from backend.engine.kite_data import exchange_request_token, login_url
from backend.services.notifications import send_telegram_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kite", tags=["Kite Auth"])

_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


def _update_env_token(access_token: str) -> None:
    """Write KITE_ACCESS_TOKEN into .env, creating or replacing the existing line."""
    new_line = f"KITE_ACCESS_TOKEN={access_token}"
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH) as f:
            content = f.read()
        pattern = r"(?m)^KITE_ACCESS_TOKEN=.*$"
        if re.search(pattern, content):
            content = re.sub(pattern, new_line, content)
        else:
            content = content.rstrip("\n") + f"\n{new_line}\n"
    else:
        content = f"{new_line}\n"
    with open(_ENV_PATH, "w") as f:
        f.write(content)


@router.get("/login-url")
def get_login_url():
    """Return the Kite login URL (useful for testing / manual flow)."""
    if not settings.kite_api_key:
        return {"error": "KITE_API_KEY not set in .env"}
    return {"login_url": login_url(settings.kite_api_key)}


@router.get("/callback", response_class=HTMLResponse)
async def kite_callback(request_token: str = "", status: str = ""):
    """
    Zerodha redirects here after the user logs in.
    Exchanges request_token → access_token, saves it, notifies via Telegram.
    """
    if status != "success" or not request_token:
        logger.warning(f"[Kite] Callback failed: status={status}")
        return HTMLResponse(_html("❌ Authorization Failed",
                                  "Zerodha reported a failed login. Please try again."), status_code=400)

    if not (settings.kite_api_key and settings.kite_api_secret):
        return HTMLResponse(_html("⚠️ Not Configured",
                                  "KITE_API_KEY / KITE_API_SECRET not set in .env."), status_code=500)

    try:
        access_token = exchange_request_token(
            settings.kite_api_key, settings.kite_api_secret, request_token
        )
    except Exception as e:
        logger.error(f"[Kite] Token exchange failed: {e}")
        return HTMLResponse(_html("❌ Token Exchange Failed", str(e)), status_code=500)

    # Persist to .env so the token survives a backend restart
    try:
        _update_env_token(access_token)
    except Exception as e:
        logger.warning(f"[Kite] Could not write .env: {e}")

    # Update in-memory settings for the running process
    settings.kite_access_token = access_token
    logger.info(f"[Kite] Access token refreshed (...{access_token[-6:]})")

    await send_telegram_message(
        "✅ <b>Kite authorized for today!</b>\n"
        "RS EMA scan will run at 16:30 IST. You're all set."
    )

    return HTMLResponse(_html("✅ Kite Authorized!",
                               "Your Zerodha session is active for today. You can close this tab."))


def _html(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font-family:-apple-system,sans-serif;text-align:center;padding:3rem 1rem;
background:#f8fafc}}h1{{font-size:1.8rem;margin-bottom:.5rem}}p{{color:#64748b}}</style>
</head><body><h1>{title}</h1><p>{body}</p></body></html>"""
