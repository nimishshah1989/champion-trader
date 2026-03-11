"""
broker_client.py — Generic broker abstraction for CTS.

Supports three modes:
  - paper: simulated orders (default, safe for development)
  - jhaveri: Jhaveri Securities broker API (future implementation)
  - dhan: Dhan broker API (legacy, kept for reference)

The Risk Guardian uses this interface exclusively for order execution.
Only SELL orders may be placed autonomously (stop loss execution).
BUY orders require human approval from Telegram.
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


def get_broker_client() -> BaseBrokerClient:
    """Factory: return the appropriate broker client based on config."""
    broker_type = settings.broker_type.lower()

    if broker_type == "jhaveri":
        if not settings.broker_live_trading:
            logger.warning("Jhaveri selected but live trading disabled — using paper")
            return PaperBrokerClient()
        return JhaveriBrokerClient()
    elif broker_type == "dhan":
        # Legacy — redirect to paper for now
        logger.warning("Dhan broker deprecated — using paper mode")
        return PaperBrokerClient()
    else:
        return PaperBrokerClient()
