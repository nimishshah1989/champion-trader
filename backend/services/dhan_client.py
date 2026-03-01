"""
Dhan broker API client.
TODO: Implement in Phase 6.
"""

from backend.config import settings


class DhanClient:
    """Wrapper around Dhan Trading API for order placement and position tracking."""

    def __init__(self) -> None:
        self.client_id = settings.dhan_client_id
        self.access_token = settings.dhan_access_token
        self.base_url = "https://api.dhan.co"

    async def place_order(
        self,
        symbol: str,
        qty: int,
        price: float,
        order_type: str = "LIMIT",
        transaction_type: str = "BUY",
    ) -> dict:
        """Place an order on Dhan. TODO: implement."""
        raise NotImplementedError("Dhan order placement not yet implemented")

    async def get_positions(self) -> list:
        """Fetch current open positions from Dhan. TODO: implement."""
        raise NotImplementedError("Dhan position fetch not yet implemented")

    async def set_stop_loss(self, symbol: str, qty: int, sl_price: float) -> dict:
        """Place a stop-loss order on Dhan. TODO: implement."""
        raise NotImplementedError("Dhan SL placement not yet implemented")
