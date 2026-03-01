"""
TradingView webhook handler.
TODO: Implement in Phase 5.
"""


async def process_tradingview_alert(payload: dict) -> dict:
    """
    Parse and act on incoming TradingView alert.

    Alert types:
    - ENTRY: Stock broke trigger level -> notify via Telegram
    - SL_HIT: Stop loss triggered -> send immediate alert, monitor 10 mins
    - PPC_DETECTED: PPC candle found -> add to scan results
    - NPC_DETECTED: NPC candle found -> flag sector as weak

    TODO: implement routing logic.
    """
    raise NotImplementedError("TradingView webhook processing not yet implemented")
