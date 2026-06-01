"""Atlas (Supabase) OHLCV adapter (A2b) — REST puller, leakage-safe.

Pulls daily OHLCV (+ delivery_pct, the NSE accumulation tell) from the Atlas
``de_equity_ohlcv`` parent table over HTTPS — the only transport open in this
sandbox (Postgres ports are firewalled). Filters by instrument_id (indexed),
paginates, and retries transient 5xx. Same ``Bar`` contract as the Kite adapter.

The HTTP layer is injectable (``http_get``) so pagination + the leakage guard are
unit-tested offline.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from decimal import Decimal
from typing import Callable, Optional

from backend.engine.kite_data import Bar

PAGE = 1000


def _default_http_get(url: str, headers: dict, timeout: int = 90) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout).read()


class AtlasOHLCVAdapter:
    def __init__(
        self,
        base_url: str,
        service_key: str,
        http_get: Optional[Callable[[str, dict], bytes]] = None,
        retries: int = 3,
    ) -> None:
        self._url = base_url.rstrip("/")
        self._headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
        self._get = http_get or _default_http_get
        self._retries = retries
        self._iid_cache: dict[str, str] = {}

    def _req(self, path: str) -> list[dict]:
        last: Optional[Exception] = None
        for attempt in range(self._retries):
            try:
                return json.loads(self._get(f"{self._url}/rest/v1/{path}", self._headers))
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code >= 500:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise
            except Exception as exc:  # transient network
                last = exc
                time.sleep(1.5 * (attempt + 1))
        raise last  # type: ignore[misc]

    def instrument_id(self, symbol: str) -> str:
        if symbol not in self._iid_cache:
            sym = urllib.parse.quote(symbol, safe="")   # encode '&' etc. (M&M, J&KBANK)
            rows = self._req(f"de_instrument?symbol=eq.{sym}&select=id&limit=1")
            if not rows:
                raise KeyError(f"{symbol} not in de_instrument")
            self._iid_cache[symbol] = rows[0]["id"]
        return self._iid_cache[symbol]

    def daily_bars(
        self, symbol: str, start: date, end: date, as_of: Optional[date] = None
    ) -> list[Bar]:
        effective_end = min(end, as_of) if as_of is not None else end
        if start > effective_end:
            return []
        iid = self.instrument_id(symbol)
        bars: list[Bar] = []
        offset = 0
        while True:
            path = (
                f"de_equity_ohlcv?instrument_id=eq.{iid}"
                f"&date=gte.{start.isoformat()}&date=lte.{effective_end.isoformat()}"
                f"&select=date,open,high,low,close,volume,delivery_pct"
                f"&order=date.asc&limit={PAGE}&offset={offset}"
            )
            rows = self._req(path)
            for r in rows:
                d = date.fromisoformat(r["date"][:10])
                if as_of is not None and d > as_of:        # leakage guard (belt-and-suspenders)
                    continue
                dp = float(r["delivery_pct"]) if r.get("delivery_pct") is not None else None
                bars.append(
                    Bar(d, Decimal(str(r["open"])), Decimal(str(r["high"])), Decimal(str(r["low"])),
                        Decimal(str(r["close"])), int(r["volume"]), dp)
                )
            if len(rows) < PAGE:
                break
            offset += PAGE
        return bars
