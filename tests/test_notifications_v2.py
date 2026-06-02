"""Tests for the v2 Telegram fill formatters (notifications.send_entry_fills/send_exit_fills).

Confirms message formatting (via a stubbed transport) and the safe no-ops: empty lists send
nothing, and an unconfigured bot returns False without raising."""
from decimal import Decimal

import pytest

from backend.services import notifications
from backend.services.notifications import send_entry_fills, send_exit_fills


@pytest.mark.asyncio
async def test_entry_fills_formats_message(monkeypatch):
    sent = {}

    async def fake_send(text):
        sent["text"] = text
        return True

    monkeypatch.setattr(notifications, "send_telegram_message", fake_send)
    ok = await send_entry_fills([
        {"symbol": "AAA", "shares": 10, "entry": Decimal("100.50"), "stop": Decimal("95.25")},
    ])
    assert ok is True
    assert "v2 ENTRIES" in sent["text"] and "AAA" in sent["text"] and "95.25" in sent["text"]


@pytest.mark.asyncio
async def test_exit_fills_formats_reason_and_r(monkeypatch):
    sent = {}

    async def fake_send(text):
        sent["text"] = text
        return True

    monkeypatch.setattr(notifications, "send_telegram_message", fake_send)
    ok = await send_exit_fills([
        {"symbol": "BBB", "fill": Decimal("88.0"), "reason": "CLOSE", "r_multiple": Decimal("-1.0")},
    ])
    assert ok is True
    assert "v2 EXITS" in sent["text"] and "BBB" in sent["text"]
    assert "CLOSE" in sent["text"] and "-1.00R" in sent["text"]


@pytest.mark.asyncio
async def test_empty_fills_send_nothing():
    assert await send_entry_fills([]) is False
    assert await send_exit_fills([]) is False


@pytest.mark.asyncio
async def test_unconfigured_bot_is_a_safe_noop():
    # default settings carry no telegram token -> send returns False, never raises
    out = await send_entry_fills([{"symbol": "AAA", "shares": 1,
                                   "entry": Decimal("10"), "stop": Decimal("9")}])
    assert out is False
