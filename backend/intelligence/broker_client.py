"""
broker_client.py — Generic broker abstraction for CTS.

Supports:
  - paper: simulated orders (default, safe — the v2 paper engine fills here)
  - kite:  Zerodha Kite Connect — the SAME provider as the data feed (Phase-2, scaffold)
  - jhaveri: Jhaveri Securities broker API (placeholder)

KILL-SWITCH: real-money order routes are gated by settings.broker_live_trading (default
False). The factory returns a live client ONLY when that flag is True, and the live clients
refuse to instantiate without it — defense in depth so no real order can fire by accident.
The v2 paper pipeline never touches this module; wiring live fills through it is Phase 2.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class BaseBrokerClient(ABC):
    """Abstract broker interface. All broker implementations must follow this."""

    @abstractmethod
    async def place_limit_order(
        self, symbol: str, qty: int, price: float, order_type: str = "BUY"
    ) -> dict:
        """Place a limit order. Returns {"order_id": str, "status": str}."""
        ...

    @abstractmethod
    async def place_market_order(
        self, symbol: str, qty: int, order_type: str = "SELL"
    ) -> dict:
        """Place a market order. Returns {"order_id": str, "status": str}."""
        ...

    @abstractmethod
    async def get_order_status(self, order_id: str) -> dict:
        """Get order status. Returns {"status": "OPEN"|"FILLED"|"REJECTED", ...}."""
        ...

    @abstractmethod
    async def get_live_price(self, symbol: str) -> float:
        """Get current live price for a symbol."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True if cancelled."""
        ...

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        """Get all open positions."""
        ...


class PaperBrokerClient(BaseBrokerClient):
    """
    Paper trading broker — simulates orders without real execution.
    Used for development, testing, and shadow portfolio tracking.
    """

    def __init__(self):
        self._orders: dict[str, dict] = {}
        self._order_counter = 0
        logger.info("Paper broker client initialized")

    async def place_limit_order(
        self, symbol: str, qty: int, price: float, order_type: str = "BUY"
    ) -> dict:
        self._order_counter += 1
        order_id = f"PAPER-{self._order_counter:06d}"

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "order_type": order_type,
            "execution_type": "LIMIT",
            "status": "FILLED",  # Paper orders fill instantly
            "filled_at": datetime.now().isoformat(),
            "fill_price": price,
        }
        self._orders[order_id] = order

        logger.info(f"[PAPER] {order_type} LIMIT: {qty} x {symbol} @ ₹{price:.2f} → {order_id}")
        return {"order_id": order_id, "status": "FILLED", "fill_price": price}

    async def place_market_order(
        self, symbol: str, qty: int, order_type: str = "SELL"
    ) -> dict:
        import yfinance as yf

        self._order_counter += 1
        order_id = f"PAPER-{self._order_counter:06d}"

        # Get approximate market price
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            price = ticker.info.get("regularMarketPrice", 0) or ticker.info.get("previousClose", 0)
        except Exception:
            price = 0.0

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "order_type": order_type,
            "execution_type": "MARKET",
            "status": "FILLED",
            "filled_at": datetime.now().isoformat(),
            "fill_price": price,
        }
        self._orders[order_id] = order

        logger.info(f"[PAPER] {order_type} MARKET: {qty} x {symbol} @ ≈₹{price:.2f} → {order_id}")
        return {"order_id": order_id, "status": "FILLED", "fill_price": price}

    async def get_order_status(self, order_id: str) -> dict:
        order = self._orders.get(order_id)
        if not order:
            return {"status": "NOT_FOUND", "order_id": order_id}
        return order

    async def get_live_price(self, symbol: str) -> float:
        import yfinance as yf
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            price = ticker.info.get("regularMarketPrice") or ticker.info.get("previousClose", 0)
            return float(price)
        except Exception as e:
            logger.error(f"Failed to get live price for {symbol}: {e}")
            return 0.0

    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            self._orders[order_id]["status"] = "CANCELLED"
            logger.info(f"[PAPER] Order {order_id} cancelled")
            return True
        return False

    async def get_positions(self) -> list[dict]:
        # Paper broker tracks positions from filled orders
        return [o for o in self._orders.values() if o["status"] == "FILLED"]


class JhaveriBrokerClient(BaseBrokerClient):
    """
    Jhaveri Securities broker API client.
    Placeholder — to be implemented when API credentials and docs are available.
    """

    def __init__(self):
        logger.info("Jhaveri broker client initialized (awaiting API integration)")

    async def place_limit_order(
        self, symbol: str, qty: int, price: float, order_type: str = "BUY"
    ) -> dict:
        raise NotImplementedError("Jhaveri broker integration pending — use paper mode")

    async def place_market_order(
        self, symbol: str, qty: int, order_type: str = "SELL"
    ) -> dict:
        raise NotImplementedError("Jhaveri broker integration pending — use paper mode")

    async def get_order_status(self, order_id: str) -> dict:
        raise NotImplementedError("Jhaveri broker integration pending")

    async def get_live_price(self, symbol: str) -> float:
        # Can still use yfinance as fallback
        import yfinance as yf
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            return float(ticker.info.get("regularMarketPrice", 0))
        except Exception:
            return 0.0

    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Jhaveri broker integration pending")

    async def get_positions(self) -> list[dict]:
        raise NotImplementedError("Jhaveri broker integration pending")


class KiteBrokerClient(BaseBrokerClient):
    """Zerodha Kite Connect execution — the Phase-2 real-money provider (scaffold).

    Matches the data feed (Kite), so feed + execution share one auth/session. The order
    methods are stubs until the live integration + reconciliation in Phase 2; instantiation
    is hard-gated on the kill-switch so this can never place an order by accident.
    """

    def __init__(self):
        if not settings.broker_live_trading:
            raise RuntimeError("KiteBrokerClient requires broker_live_trading=True (kill-switch)")
        if not (settings.kite_api_key and settings.kite_access_token):
            raise RuntimeError("Kite live trading needs KITE_API_KEY / KITE_ACCESS_TOKEN")
        logger.warning("KiteBrokerClient initialised — LIVE order routing armed")

    async def place_limit_order(self, symbol: str, qty: int, price: float,
                                order_type: str = "BUY") -> dict:
        raise NotImplementedError("Kite live order routing — Phase 2 (paper run must pass first)")

    async def place_market_order(self, symbol: str, qty: int, order_type: str = "SELL") -> dict:
        raise NotImplementedError("Kite live order routing — Phase 2 (paper run must pass first)")

    async def get_order_status(self, order_id: str) -> dict:
        raise NotImplementedError("Kite live order routing — Phase 2")

    async def get_live_price(self, symbol: str) -> float:
        raise NotImplementedError("Kite live quote — Phase 2")

    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Kite live order routing — Phase 2")

    async def get_positions(self) -> list[dict]:
        raise NotImplementedError("Kite live order routing — Phase 2")


def get_broker_client() -> BaseBrokerClient:
    """Factory: return a broker client per config. Live clients only when the kill-switch is on."""
    broker_type = settings.broker_type.lower()

    if not settings.broker_live_trading:
        if broker_type not in ("paper", ""):
            logger.warning(f"{broker_type} selected but live trading disabled — using paper")
        return PaperBrokerClient()           # kill-switch OFF -> always paper

    if broker_type == "kite":
        return KiteBrokerClient()
    if broker_type == "jhaveri":
        return JhaveriBrokerClient()
    logger.warning(f"Unknown live broker '{broker_type}' — refusing live, using paper")
    return PaperBrokerClient()
