"""Tests for the broker kill-switch — no real order can fire unless broker_live_trading is on.

Verifies the factory returns the safe PaperBrokerClient whenever the switch is off (even if a
live broker_type is configured), that the live Kite client refuses to instantiate without the
switch or without creds, and that its order methods raise (never silently 'succeed')."""
import pytest

from backend.config import settings
from backend.intelligence.broker_client import (
    KiteBrokerClient,
    PaperBrokerClient,
    get_broker_client,
)


def test_factory_returns_paper_when_killswitch_off(monkeypatch):
    monkeypatch.setattr(settings, "broker_live_trading", False)
    monkeypatch.setattr(settings, "broker_type", "kite")     # live type requested...
    assert isinstance(get_broker_client(), PaperBrokerClient)  # ...but switch off -> paper


def test_kite_client_refuses_without_killswitch(monkeypatch):
    monkeypatch.setattr(settings, "broker_live_trading", False)
    with pytest.raises(RuntimeError):
        KiteBrokerClient()


def test_kite_client_refuses_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "broker_live_trading", True)
    monkeypatch.setattr(settings, "kite_api_key", "")
    monkeypatch.setattr(settings, "kite_access_token", "")
    with pytest.raises(RuntimeError):
        KiteBrokerClient()


def test_factory_returns_kite_only_when_armed(monkeypatch):
    monkeypatch.setattr(settings, "broker_live_trading", True)
    monkeypatch.setattr(settings, "broker_type", "kite")
    monkeypatch.setattr(settings, "kite_api_key", "k")
    monkeypatch.setattr(settings, "kite_access_token", "t")
    assert isinstance(get_broker_client(), KiteBrokerClient)


@pytest.mark.asyncio
async def test_kite_orders_raise_not_silently_succeed(monkeypatch):
    monkeypatch.setattr(settings, "broker_live_trading", True)
    monkeypatch.setattr(settings, "kite_api_key", "k")
    monkeypatch.setattr(settings, "kite_access_token", "t")
    client = KiteBrokerClient()
    with pytest.raises(NotImplementedError):
        await client.place_market_order("AAA", 1, "SELL")
    with pytest.raises(NotImplementedError):
        await client.place_limit_order("AAA", 1, 100.0, "BUY")
