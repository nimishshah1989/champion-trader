#!/usr/bin/env python3
"""Production health check — runs against live champion.jslwealth.in.

Usage:
    python scripts/production_health_check.py
    python scripts/production_health_check.py --notify   # Send Telegram on failure
    python scripts/production_health_check.py --json     # JSON output

Exit codes:
    0 = all checks pass
    1 = one or more checks failed
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

API_BASE = "https://champion-api.jslwealth.in"
FRONTEND_BASE = "https://champion.jslwealth.in"
TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# HTTP helper (stdlib only — no external deps)
# ---------------------------------------------------------------------------

def fetch(url: str, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[int, Any]:
    """Make an HTTP request, return (status_code, parsed_json_or_text)."""
    data = None
    headers = {"Content-Type": "application/json"}
    if body:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            return e.code, json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return e.code, raw
    except Exception as exc:
        return 0, str(exc)


# ---------------------------------------------------------------------------
# Check definitions
# ---------------------------------------------------------------------------

class CheckResult:
    def __init__(self, name: str, passed: bool, detail: str = "", duration_ms: int = 0):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
        }


def _timed(func):  # type: ignore[no-untyped-def]
    """Wrapper that times a check function."""
    def wrapper(*args, **kwargs) -> CheckResult:  # type: ignore[no-untyped-def]
        start = time.monotonic()
        result = func(*args, **kwargs)
        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result
    return wrapper


@_timed
def check_api_health() -> CheckResult:
    status, data = fetch(f"{API_BASE}/health")
    if status != 200:
        return CheckResult("API Health", False, f"HTTP {status}")
    if not isinstance(data, dict) or data.get("status") != "ok":
        return CheckResult("API Health", False, f"Unexpected: {data}")
    scheduler = data.get("scheduler", "unknown")
    jobs = data.get("scheduled_jobs", 0)
    return CheckResult("API Health", True, f"scheduler={scheduler}, {jobs} jobs")


@_timed
def check_scheduler_running() -> CheckResult:
    status, data = fetch(f"{API_BASE}/health")
    if status != 200:
        return CheckResult("Scheduler Running", False, f"HTTP {status}")
    if data.get("scheduler") != "running":
        return CheckResult("Scheduler Running", False, f"scheduler={data.get('scheduler')}")
    jobs = data.get("scheduled_jobs", 0)
    if jobs < 8:
        return CheckResult("Scheduler Running", False, f"Only {jobs} jobs (expected 10)")
    return CheckResult("Scheduler Running", True, f"{jobs} jobs active")


@_timed
def check_api_endpoint(name: str, path: str, expect_type: type = list) -> CheckResult:
    status, data = fetch(f"{API_BASE}{path}")
    if status != 200:
        return CheckResult(f"API {name}", False, f"HTTP {status}: {str(data)[:200]}")
    if not isinstance(data, expect_type):
        return CheckResult(f"API {name}", False, f"Expected {expect_type.__name__}, got {type(data).__name__}")
    return CheckResult(f"API {name}", True, f"{len(data) if isinstance(data, list) else 'ok'} items")


@_timed
def check_calculator_decimal_fix() -> CheckResult:
    """Critical: verify Decimal→float middleware works (the production bug)."""
    body = {
        "account_value": 500000,
        "rpt_pct": 0.5,
        "entry_price": 601,
        "trp_pct": 3.18,
        "symbol": "ASTERDM",
    }
    status, data = fetch(f"{API_BASE}/calculator/position", method="POST", body=body)
    if status != 200:
        return CheckResult("Calculator Decimal Fix", False, f"HTTP {status}: {str(data)[:200]}")

    # Verify ALL numeric fields are actual numbers, not strings
    numeric_fields = [
        "rpt_amount", "sl_price", "sl_pct", "sl_amount",
        "position_value", "position_size", "half_qty",
        "target_2r", "target_ne", "target_ge", "target_ee",
    ]
    string_fields = []
    for field in numeric_fields:
        val = data.get(field)
        if isinstance(val, str):
            string_fields.append(f"{field}={val!r}")

    if string_fields:
        return CheckResult(
            "Calculator Decimal Fix", False,
            f"Decimal→string bug! Fields still strings: {', '.join(string_fields)}",
        )

    # Verify known values
    if data.get("position_size") != 131:
        return CheckResult(
            "Calculator Decimal Fix", False,
            f"position_size={data.get('position_size')}, expected 131",
        )
    if data.get("half_qty") != 65:
        return CheckResult(
            "Calculator Decimal Fix", False,
            f"half_qty={data.get('half_qty')}, expected 65",
        )

    return CheckResult("Calculator Decimal Fix", True, "All fields numeric, values correct")


@_timed
def check_scanner_data_types() -> CheckResult:
    """Verify scanner results have numeric fields as numbers, not strings."""
    status, data = fetch(f"{API_BASE}/scanner/results/latest")
    if status != 200:
        return CheckResult("Scanner Data Types", False, f"HTTP {status}")
    if not isinstance(data, list) or len(data) == 0:
        return CheckResult("Scanner Data Types", True, "No scan data (empty is OK)")

    item = data[0]
    numeric_fields = ["close_price", "trp", "volume_ratio", "avg_trp", "adt", "trigger_level"]
    string_fields = []
    for field in numeric_fields:
        val = item.get(field)
        if val is not None and isinstance(val, str):
            string_fields.append(f"{field}={val!r}")

    if string_fields:
        return CheckResult(
            "Scanner Data Types", False,
            f"Decimal→string bug! {', '.join(string_fields)}",
        )
    return CheckResult("Scanner Data Types", True, f"{len(data)} results, all types correct")


@_timed
def check_frontend_page(name: str, path: str) -> CheckResult:
    status, body = fetch(f"{FRONTEND_BASE}{path}")
    if status != 200:
        return CheckResult(f"Frontend {name}", False, f"HTTP {status}")
    if isinstance(body, str) and "Champion Trader" in body:
        return CheckResult(f"Frontend {name}", True)
    if isinstance(body, str) and "<!DOCTYPE html>" in body:
        return CheckResult(f"Frontend {name}", True)
    return CheckResult(f"Frontend {name}", False, "Missing expected HTML content")


@_timed
def check_negative_422() -> CheckResult:
    """POST with missing required fields should return 422."""
    status, _ = fetch(f"{API_BASE}/calculator/position", method="POST", body={"symbol": "TEST"})
    if status == 422:
        return CheckResult("Negative: 422 on bad input", True)
    return CheckResult("Negative: 422 on bad input", False, f"Expected 422, got {status}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_checks() -> list[CheckResult]:
    results: list[CheckResult] = []

    # Infrastructure
    results.append(check_api_health())
    results.append(check_scheduler_running())

    # Critical bug regression
    results.append(check_calculator_decimal_fix())
    results.append(check_scanner_data_types())

    # API endpoints
    results.append(check_api_endpoint("Scanner Latest", "/scanner/results/latest"))
    results.append(check_api_endpoint("Watchlist", "/watchlist"))
    results.append(check_api_endpoint("Trades", "/trades"))
    results.append(check_api_endpoint("Trade Stats", "/trades/stats", dict))
    results.append(check_api_endpoint("Market Stance", "/market-stance/latest", (dict, type(None))))  # type: ignore[arg-type]
    results.append(check_api_endpoint("Alerts", "/alerts"))
    results.append(check_api_endpoint("Unread Count", "/alerts/unread-count", dict))
    results.append(check_api_endpoint("Journal", "/journal"))
    results.append(check_api_endpoint("Actions", "/actions"))
    results.append(check_api_endpoint("Simulation Runs", "/simulation/runs"))

    # Intelligence endpoints
    results.append(check_api_endpoint("Regime", "/api/intelligence/regime", dict))
    results.append(check_api_endpoint("Optimize Status", "/api/intelligence/optimize/status", dict))

    # Frontend pages
    for name, path in [
        ("Dashboard", "/"),
        ("Pipeline", "/pipeline"),
        ("Calculator", "/calculator"),
        ("Trades", "/trades"),
        ("Watchlist", "/watchlist"),
        ("Actions", "/actions"),
    ]:
        results.append(check_frontend_page(name, path))

    # Negative tests
    results.append(check_negative_422())

    return results


def send_telegram_notification(message: str) -> None:
    """Send failure notification via Telegram (reads from .env on server)."""
    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("[WARN] Telegram not configured, skipping notification")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        fetch(url, method="POST", body=body)
    except Exception as exc:
        print(f"[WARN] Telegram send failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Production health check")
    parser.add_argument("--notify", action="store_true", help="Send Telegram on failure")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = run_all_checks()
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    if args.json:
        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "checks": [r.to_dict() for r in results],
        }
        print(json.dumps(report, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  PRODUCTION HEALTH CHECK — champion.jslwealth.in")
        print(f"{'='*60}\n")

        for r in results:
            icon = "\u2705" if r.passed else "\u274c"
            detail = f" — {r.detail}" if r.detail else ""
            ms = f" ({r.duration_ms}ms)" if r.duration_ms else ""
            print(f"  {icon} {r.name}{detail}{ms}")

        print(f"\n{'='*60}")
        print(f"  RESULT: {len(passed)} passed, {len(failed)} failed out of {len(results)}")
        print(f"{'='*60}\n")

        if failed:
            print("  FAILURES:")
            for r in failed:
                print(f"    \u274c {r.name}: {r.detail}")
            print()

    if failed and args.notify:
        msg = (
            f"\U0001f534 <b>CTS Production Check FAILED</b>\n\n"
            f"{len(failed)} of {len(results)} checks failed:\n"
        )
        for r in failed:
            msg += f"  \u274c {r.name}: {r.detail}\n"
        send_telegram_notification(msg)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
