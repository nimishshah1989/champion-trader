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
from typing import Any

API_BASE = "https://champion-api.jslwealth.in"
FRONTEND_BASE = "https://champion.jslwealth.in"
TIMEOUT_SECONDS = 15


def fetch(url: str, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[int, Any]:
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


class CheckResult:
    def __init__(self, name: str, passed: bool, detail: str = "", duration_ms: int = 0):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed,
                "detail": self.detail, "duration_ms": self.duration_ms}


def _timed(func):  # type: ignore[no-untyped-def]
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
        return CheckResult("Scheduler Running", False, f"Only {jobs} jobs (expected ≥8)")
    return CheckResult("Scheduler Running", True, f"{jobs} jobs active")


@_timed
def check_api_endpoint(name: str, path: str, expect_type: type = list) -> CheckResult:
    status, data = fetch(f"{API_BASE}{path}")
    if status != 200:
        return CheckResult(f"API {name}", False, f"HTTP {status}: {str(data)[:200]}")
    if not isinstance(data, expect_type):
        return CheckResult(f"API {name}", False,
                           f"Expected {expect_type.__name__}, got {type(data).__name__}")
    return CheckResult(f"API {name}", True,
                       f"{len(data) if isinstance(data, list) else 'ok'} items")


@_timed
def check_decimal_fix() -> CheckResult:
    """Verify Decimal→float middleware: scanner results must have numeric fields."""
    status, data = fetch(f"{API_BASE}/scanner/results/latest")
    if status != 200:
        return CheckResult("Decimal Fix (Scanner)", False, f"HTTP {status}")
    if not isinstance(data, list) or len(data) == 0:
        return CheckResult("Decimal Fix (Scanner)", True, "No scan data yet — skipped")
    item = data[0]
    numeric_fields = ["close_price", "trp", "volume_ratio", "avg_trp", "adt", "trigger_level"]
    bad = [f for f in numeric_fields if item.get(f) is not None and isinstance(item.get(f), str)]
    if bad:
        return CheckResult("Decimal Fix (Scanner)", False, f"Still strings: {bad}")
    return CheckResult("Decimal Fix (Scanner)", True, "All numeric fields are numbers")


@_timed
def check_trades_decimal_fix() -> CheckResult:
    """Verify Decimal→float middleware: trade stats must have numeric fields."""
    status, data = fetch(f"{API_BASE}/trades/stats")
    if status != 200:
        return CheckResult("Decimal Fix (Trades)", False, f"HTTP {status}")
    if not isinstance(data, dict):
        return CheckResult("Decimal Fix (Trades)", False, "Expected dict")
    bad = [k for k, v in data.items() if isinstance(v, str) and k not in ("status",)]
    if bad:
        return CheckResult("Decimal Fix (Trades)", False, f"Still strings: {bad}")
    return CheckResult("Decimal Fix (Trades)", True, "All numeric fields are numbers")


@_timed
def check_frontend_page(name: str, path: str) -> CheckResult:
    status, body = fetch(f"{FRONTEND_BASE}{path}")
    if status != 200:
        return CheckResult(f"Frontend {name}", False, f"HTTP {status}")
    if isinstance(body, str) and ("<!DOCTYPE html>" in body or "Champion Trader" in body):
        return CheckResult(f"Frontend {name}", True)
    return CheckResult(f"Frontend {name}", False, "Missing expected HTML content")


@_timed
def check_kite_auth_endpoint() -> CheckResult:
    """Kite login-url endpoint — returns error if unconfigured, but must not 404."""
    status, data = fetch(f"{API_BASE}/kite/login-url")
    if status == 404:
        return CheckResult("Kite Auth Endpoint", False, "Router not registered (404)")
    return CheckResult("Kite Auth Endpoint", True, f"HTTP {status}")


def run_all_checks() -> list[CheckResult]:
    results: list[CheckResult] = []

    # Infrastructure
    results.append(check_api_health())
    results.append(check_scheduler_running())

    # Decimal middleware regression
    results.append(check_decimal_fix())
    results.append(check_trades_decimal_fix())

    # v2 Pipeline API
    results.append(check_api_endpoint("Scanner Latest", "/scanner/results/latest"))
    results.append(check_api_endpoint("Watchlist", "/watchlist"))
    results.append(check_api_endpoint("Trades", "/trades"))
    results.append(check_api_endpoint("Trade Stats", "/trades/stats", dict))
    results.append(check_api_endpoint("Journal", "/journal"))

    # Intelligence API
    results.append(check_api_endpoint("Regime", "/api/intelligence/regime", dict))
    results.append(check_api_endpoint("Daily Brief", "/api/intelligence/brief", dict))
    results.append(check_api_endpoint("Risk Status", "/api/intelligence/risk/status", dict))
    results.append(check_api_endpoint("Optimize Status", "/api/intelligence/optimize/status", dict))
    results.append(check_api_endpoint("Attribution", "/api/intelligence/attribution", dict))
    results.append(check_api_endpoint("Shadow", "/api/intelligence/shadow", dict))

    # RS EMA Strategy API
    results.append(check_api_endpoint("RS EMA Status", "/rs-strategy/status", dict))
    results.append(check_api_endpoint("RS EMA Trades", "/rs-strategy/trades", dict))

    # Kite auth
    results.append(check_kite_auth_endpoint())

    # Frontend pages
    for name, path in [
        ("Dashboard", "/"),
        ("Pipeline", "/pipeline"),
        ("Trades", "/trades"),
        ("Review", "/review"),
        ("RS Strategy", "/rs-strategy"),
        ("Intelligence", "/intelligence"),
    ]:
        results.append(check_frontend_page(name, path))

    return results


def send_telegram_notification(message: str) -> None:
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
            icon = "✅" if r.passed else "❌"
            detail = f" — {r.detail}" if r.detail else ""
            ms = f" ({r.duration_ms}ms)" if r.duration_ms else ""
            print(f"  {icon} {r.name}{detail}{ms}")
        print(f"\n{'='*60}")
        print(f"  RESULT: {len(passed)} passed, {len(failed)} failed out of {len(results)}")
        print(f"{'='*60}\n")
        if failed:
            print("  FAILURES:")
            for r in failed:
                print(f"    ❌ {r.name}: {r.detail}")
            print()

    if failed and args.notify:
        msg = (
            f"🔴 <b>CTS Production Check FAILED</b>\n\n"
            f"{len(failed)} of {len(results)} checks failed:\n"
        )
        for r in failed:
            msg += f"  ❌ {r.name}: {r.detail}\n"
        send_telegram_notification(msg)
    elif args.notify and not failed:
        send_telegram_notification("✅ <b>CTS Production Check PASSED</b> — all systems nominal.")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
