"""Kite historical data adapter (A2) — point-in-time, leakage-safe daily bars.

Feeds the backtest engine clean OHLCV. The HTTP layer is injectable
(``http_get``) so the logic — symbol→token mapping, parsing, and the leakage
guard — is fully unit-tested with no network. All prices are ``Decimal``.

Leakage guard: given ``as_of``, the adapter never requests or returns a bar
dated after it. This is the single most important property — a leak silently
manufactures a fake edge in the backtest.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Optional

KITE_BASE = "https://api.kite.trade"


# --- Daily login / access-token exchange (the access_token expires every morning) --------

def login_url(api_key: str) -> str:
    """The Kite Connect login URL. After login it redirects to your app's redirect URL with
    ``?request_token=...&status=success`` — paste that request_token into kite_login.py."""
    return f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"


def session_checksum(api_key: str, request_token: str, api_secret: str) -> str:
    """Kite session checksum = SHA-256(api_key + request_token + api_secret)."""
    return hashlib.sha256(f"{api_key}{request_token}{api_secret}".encode()).hexdigest()


def _default_http_post(url: str, fields: dict, timeout: int = 30) -> bytes:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={"X-Kite-Version": "3"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def exchange_request_token(api_key: str, api_secret: str, request_token: str, *,
                           http_post: Optional[Callable[[str, dict], bytes]] = None) -> str:
    """Exchange a one-time request_token for today's access_token (the Kite session API).

    The HTTP layer is injectable for testing; the checksum + response parsing are pure.
    Raises RuntimeError if Kite doesn't return a success payload with an access_token.
    """
    post = http_post or _default_http_post
    raw = post(f"{KITE_BASE}/session/token", {
        "api_key": api_key,
        "request_token": request_token,
        "checksum": session_checksum(api_key, request_token, api_secret),
    })
    payload = json.loads(raw)
    token = payload.get("data", {}).get("access_token") if payload.get("status") == "success" else None
    if not token:
        raise RuntimeError(f"Kite session exchange failed: {payload}")
    return token


@dataclass(frozen=True)
class Bar:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    delivery_pct: Optional[float] = None   # NSE delivery %, when available (Atlas); None for Kite


def _default_http_get(url: str, api_key: str, access_token: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"X-Kite-Version": "3", "Authorization": f"token {api_key}:{access_token}"},
    )
    return urllib.request.urlopen(req, timeout=timeout).read()


class KiteHistoricalAdapter:
    """Fetches NSE daily OHLCV from Kite, leakage-safe.

    Args:
        api_key / access_token: Kite credentials (access_token refreshed daily).
        http_get: optional transport ``(url) -> bytes`` for testing; defaults to
            a urllib-based call carrying the auth header.
    """

    def __init__(
        self,
        api_key: str,
        access_token: str,
        http_get: Optional[Callable[[str], bytes]] = None,
    ) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._http_get: Callable[[str], bytes] = http_get or (
            lambda url: _default_http_get(url, api_key, access_token)
        )
        self._instruments: Optional[dict[str, int]] = None

    def _load_instruments(self, exchange: str = "NSE") -> dict[str, int]:
        if self._instruments is None:
            raw = self._http_get(f"{KITE_BASE}/instruments/{exchange}").decode()
            rows = csv.DictReader(io.StringIO(raw))
            self._instruments = {
                r["tradingsymbol"]: int(r["instrument_token"])
                for r in rows
                if r.get("tradingsymbol") and r.get("instrument_token")
            }
        return self._instruments

    def instrument_token(self, symbol: str, exchange: str = "NSE") -> int:
        tokens = self._load_instruments(exchange)
        if symbol not in tokens:
            raise KeyError(f"{symbol} not found in {exchange} instruments")
        return tokens[symbol]

    def daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        as_of: Optional[date] = None,
    ) -> list[Bar]:
        """Daily OHLCV for ``symbol`` in [start, end], never beyond ``as_of``."""
        # Leakage guard #1: never request data after as_of.
        effective_end = min(end, as_of) if as_of is not None else end
        if start > effective_end:
            return []

        token = self.instrument_token(symbol)
        url = (
            f"{KITE_BASE}/instruments/historical/{token}/day"
            f"?from={start.isoformat()}&to={effective_end.isoformat()}"
        )
        payload = json.loads(self._http_get(url).decode())
        candles = payload.get("data", {}).get("candles", [])

        bars: list[Bar] = []
        for c in candles:
            d = date.fromisoformat(c[0][:10])
            # Leakage guard #2 (belt-and-suspenders): drop anything past as_of.
            if as_of is not None and d > as_of:
                continue
            bars.append(
                Bar(d, Decimal(str(c[1])), Decimal(str(c[2])), Decimal(str(c[3])), Decimal(str(c[4])), int(c[5]))
            )
        return bars
