"""Middleware to convert Pydantic v2 Decimal-as-string back to JSON floats.

Pydantic v2 serialises ``Decimal`` fields as strings (``"4.24"``).  The
frontend expects plain numbers (calls ``.toFixed()`` etc.).  This middleware
intercepts every ``application/json`` response, walks the parsed JSON tree,
and converts any string value that matches a pure numeric pattern back to a
``float``.

Non-numeric strings (dates, symbols, text) are never touched because the
regex requires the *entire* value to be a bare number.
"""

import json as _json
import logging
import re as _re
from typing import Any, Union

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Matches strings that are pure signed decimals: "4.24", "-19.11", "500000"
# Does NOT match dates ("2026-03-16"), symbols ("ASTERDM"), or mixed text.
_NUMERIC_RE = _re.compile(r"^-?\d+(\.\d+)?$")


def _convert_strings_to_numbers(obj: Any) -> Any:
    """Recursively convert string-encoded numbers in a parsed JSON object."""
    if isinstance(obj, dict):
        return {k: _convert_strings_to_numbers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_strings_to_numbers(i) for i in obj]
    if isinstance(obj, str) and _NUMERIC_RE.match(obj):
        try:
            return float(obj)
        except (ValueError, OverflowError):
            return obj
    return obj


class DecimalFixMiddleware(BaseHTTPMiddleware):
    """Convert Pydantic's Decimal-as-string back to JSON numbers."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Consume the streaming body
        body_chunks: list[Union[bytes, str]] = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
        body = b"".join(body_chunks)  # type: ignore[arg-type]

        try:
            data = _json.loads(body)
            fixed = _convert_strings_to_numbers(data)
            new_body = _json.dumps(
                fixed, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        except (ValueError, TypeError):
            logger.debug("DecimalFixMiddleware: could not parse JSON body, passing through")
            new_body = body

        # Drop stale content-length; Response will recalculate from new_body
        new_headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower() not in ("content-length", "content-type")
        }

        return Response(
            content=new_body,
            status_code=response.status_code,
            headers=new_headers,
            media_type="application/json",
        )
