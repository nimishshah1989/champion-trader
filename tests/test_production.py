#!/usr/bin/env python3
"""
Champion Trader System -- Production E2E Test Suite.

Runs against live production endpoints and validates:
  - Every API endpoint returns expected status codes
  - Response schemas match expected shapes
  - All numeric fields are actual numbers (not strings) -- the Decimal bug guard
  - Calculator produces correct values for known inputs
  - Frontend pages load and serve assets
  - Negative/error paths return proper HTTP codes

Usage:
    python tests/test_production.py
    python tests/test_production.py --base-url https://champion-api.jslwealth.in
    python tests/test_production.py --frontend-url https://champion.jslwealth.in

Exit code 0 = all tests passed.  Exit code 1 = at least one failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional


try:
    import requests
except ImportError:
    print("ERROR: 'requests' package is required.  pip install requests")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_API_URL = "https://champion-api.jslwealth.in"
DEFAULT_FRONTEND_URL = "https://champion.jslwealth.in"
REQUEST_TIMEOUT = 30  # seconds per request


# ---------------------------------------------------------------------------
# Test result collection
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    detail: str = ""
    category: str = "general"


@dataclass
class TestReport:
    results: list[TestResult] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0

    def add(self, result: TestResult) -> None:
        self.results.append(result)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "all_passed": self.all_passed,
                "duration_s": round(self.finished_at - self.started_at, 2),
            },
            "tests": [
                {
                    "name": r.name,
                    "category": r.category,
                    "passed": r.passed,
                    "duration_ms": round(r.duration_ms, 1),
                    "detail": r.detail,
                }
                for r in self.results
            ],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(url: str, **kwargs: Any) -> requests.Response:
    return requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)


def _post(url: str, json_body: dict | None = None, **kwargs: Any) -> requests.Response:
    return requests.post(url, json=json_body, timeout=REQUEST_TIMEOUT, **kwargs)


def _timer() -> float:
    return time.monotonic()


def _assert_numeric(value: Any, path: str) -> list[str]:
    """Return a list of violations if value (or nested values) contains
    numeric-looking strings instead of actual int/float."""
    errors: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            errors.extend(_assert_numeric(v, f"{path}.{k}"))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            errors.extend(_assert_numeric(v, f"{path}[{i}]"))
    elif isinstance(value, str):
        # A string that looks like a number is a Decimal serialisation bug
        stripped = value.strip()
        if stripped and re.match(r"^-?\d+(\.\d+)?$", stripped):
            errors.append(f"{path} = \"{value}\" (string, expected number)")
    return errors


def _check_keys(data: dict, required_keys: list[str], path: str = "root") -> list[str]:
    missing = [k for k in required_keys if k not in data]
    if missing:
        return [f"{path} missing keys: {missing}"]
    return []


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

report = TestReport()


def run_test(
    name: str,
    fn: Any,
    category: str = "api",
) -> None:
    """Execute a test function, catch exceptions, record result."""
    t0 = _timer()
    try:
        fn()
        elapsed = (_timer() - t0) * 1000
        result = TestResult(name=name, passed=True, duration_ms=elapsed, category=category)
        print(f"  PASS  {name} ({elapsed:.0f}ms)")
    except AssertionError as exc:
        elapsed = (_timer() - t0) * 1000
        detail = str(exc)
        result = TestResult(name=name, passed=False, duration_ms=elapsed, detail=detail, category=category)
        print(f"  FAIL  {name} ({elapsed:.0f}ms)")
        print(f"        {detail}")
    except Exception as exc:
        elapsed = (_timer() - t0) * 1000
        detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        result = TestResult(name=name, passed=False, duration_ms=elapsed, detail=detail, category=category)
        print(f"  FAIL  {name} ({elapsed:.0f}ms)")
        print(f"        {type(exc).__name__}: {exc}")
    report.add(result)


# ---- API: Root & Health ----

def test_root(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"
        errs = _check_keys(data, ["name", "version"])
        assert not errs, "; ".join(errs)
        assert isinstance(data["name"], str), "name must be a string"
        assert isinstance(data["version"], str), "version must be a string"
    run_test("GET / (root)", _test, "api")


def test_health(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/health")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        errs = _check_keys(data, ["status", "scheduler", "scheduled_jobs", "jobs"])
        assert not errs, "; ".join(errs)
        assert data["status"] == "ok", f"status={data['status']}, expected 'ok'"
        assert isinstance(data["scheduled_jobs"], int), "scheduled_jobs must be int"
        assert isinstance(data["jobs"], list), "jobs must be a list"
    run_test("GET /health", _test, "api")


# ---- API: Scanner ----

def test_scanner_latest(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/scanner/results/latest")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        # Validate numeric fields are not strings
        num_errors = _assert_numeric(data, "scanner/results/latest")
        assert not num_errors, "Decimal-as-string bug detected:\n  " + "\n  ".join(num_errors)
        # If there are results, validate schema of first item
        if data:
            item = data[0]
            errs = _check_keys(item, ["id", "scan_date", "symbol", "scan_type"])
            assert not errs, "; ".join(errs)
            # Spot-check known Decimal fields
            for fld in ("trp", "close_price", "volume_ratio", "trigger_level", "avg_trp", "adt"):
                if fld in item and item[fld] is not None:
                    assert isinstance(item[fld], (int, float)), (
                        f"scanner item .{fld} = {item[fld]!r} ({type(item[fld]).__name__}), expected number"
                    )
    run_test("GET /scanner/results/latest", _test, "api")


# ---- API: Watchlist ----

def test_watchlist(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/watchlist")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        num_errors = _assert_numeric(data, "watchlist")
        assert not num_errors, "Decimal-as-string bug:\n  " + "\n  ".join(num_errors)
    run_test("GET /watchlist", _test, "api")


# ---- API: Trades ----

def test_trades(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/trades")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        num_errors = _assert_numeric(data, "trades")
        assert not num_errors, "Decimal-as-string bug:\n  " + "\n  ".join(num_errors)
    run_test("GET /trades", _test, "api")


def test_trades_stats(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/trades/stats")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"
        errs = _check_keys(data, ["total_trades", "open_trades"])
        assert not errs, "; ".join(errs)
        assert isinstance(data["total_trades"], int), "total_trades must be int"
        assert isinstance(data["open_trades"], int), "open_trades must be int"
        num_errors = _assert_numeric(data, "trades/stats")
        assert not num_errors, "Decimal-as-string bug:\n  " + "\n  ".join(num_errors)
    run_test("GET /trades/stats", _test, "api")


# ---- API: Market Stance ----

def test_market_stance(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/market-stance/latest")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        # Can be null/None or a dict
        assert data is None or isinstance(data, dict), f"Expected dict or null, got {type(data).__name__}"
        if data:
            num_errors = _assert_numeric(data, "market-stance/latest")
            assert not num_errors, "Decimal-as-string bug:\n  " + "\n  ".join(num_errors)
    run_test("GET /market-stance/latest", _test, "api")


# ---- API: Alerts ----

def test_alerts_unread_count(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/alerts/unread-count")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"
        assert "count" in data, "Missing 'count' key"
        assert isinstance(data["count"], int), f"count must be int, got {type(data['count']).__name__}"
    run_test("GET /alerts/unread-count", _test, "api")


def test_alerts(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/alerts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    run_test("GET /alerts", _test, "api")


# ---- API: Journal ----

def test_journal(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/journal")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    run_test("GET /journal", _test, "api")


# ---- API: Actions ----

def test_actions(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/actions")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    run_test("GET /actions", _test, "api")


# ---- API: Simulation ----

def test_simulation_runs(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/simulation/runs")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    run_test("GET /simulation/runs", _test, "api")


# ---- API: Intelligence ----

def test_intelligence_regime(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/api/intelligence/regime")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        # Response can be a dict or null
        data = resp.json()
        assert data is None or isinstance(data, dict), f"Expected dict or null, got {type(data).__name__}"
    run_test("GET /api/intelligence/regime", _test, "api")


def test_intelligence_optimize_status(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/api/intelligence/optimize/status")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data is None or isinstance(data, dict), f"Expected dict or null, got {type(data).__name__}"
    run_test("GET /api/intelligence/optimize/status", _test, "api")


# ---- API: Calculator (POST with known values) ----

def test_calculator_position(api: str) -> None:
    def _test() -> None:
        payload = {
            "account_value": 500000,
            "rpt_pct": 0.5,
            "entry_price": 601,
            "trp_pct": 3.18,
            "symbol": "ASTERDM",
        }
        resp = _post(f"{api}/calculator/position", json_body=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}. Body: {resp.text[:500]}"
        data = resp.json()

        # -- Schema keys --
        expected_keys = [
            "rpt_amount", "sl_price", "sl_pct", "sl_amount",
            "position_value", "position_size", "half_qty",
            "target_2r", "target_ne", "target_ge", "target_ee",
        ]
        errs = _check_keys(data, expected_keys)
        assert not errs, "; ".join(errs)

        # -- All numeric, no strings --
        num_errors = _assert_numeric(data, "calculator/position")
        assert not num_errors, "Decimal-as-string bug:\n  " + "\n  ".join(num_errors)

        # -- Known correct values (ASTERDM test case from README) --
        assert data["rpt_amount"] == 2500.0, f"rpt_amount={data['rpt_amount']}, expected 2500.0"
        assert data["position_size"] == 131, f"position_size={data['position_size']}, expected 131"
        assert data["half_qty"] == 65, f"half_qty={data['half_qty']}, expected 65"

        # sl_price should be approximately 581.89 (Entry - Entry*TRP%)
        sl = data["sl_price"]
        assert isinstance(sl, (int, float)), f"sl_price must be numeric, got {type(sl).__name__}"
        assert 581.0 <= sl <= 583.0, f"sl_price={sl}, expected ~581.89"

        # Types of numeric fields
        for fld in ("rpt_amount", "sl_price", "sl_amount", "position_value",
                     "target_2r", "target_ne", "target_ge", "target_ee"):
            assert isinstance(data[fld], (int, float)), (
                f"{fld}={data[fld]!r} is {type(data[fld]).__name__}, expected float"
            )
        assert isinstance(data["position_size"], int), "position_size must be int"
        assert isinstance(data["half_qty"], int), "half_qty must be int"

    run_test("POST /calculator/position (ASTERDM)", _test, "api")


# ---- Negative tests ----

def test_calculator_missing_fields(api: str) -> None:
    def _test() -> None:
        # Missing required fields should yield 422
        resp = _post(f"{api}/calculator/position", json_body={"account_value": 500000})
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
    run_test("POST /calculator/position (missing fields -> 422)", _test, "negative")


def test_trade_not_found(api: str) -> None:
    def _test() -> None:
        resp = _get(f"{api}/trades/99999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    run_test("GET /trades/99999 (not found -> 404)", _test, "negative")


# ---- Frontend tests ----

FRONTEND_PAGES = [
    ("/", "Champion Trader"),
    ("/pipeline", None),
    ("/calculator", None),
    ("/trades", None),
    ("/watchlist", None),
    ("/actions", None),
]


def test_frontend_page(frontend: str, path: str, contains: Optional[str]) -> None:
    def _test() -> None:
        resp = _get(f"{frontend}{path}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} for {frontend}{path}"
        if contains:
            assert contains.lower() in resp.text.lower(), (
                f"Page {path} does not contain '{contains}'"
            )
    run_test(f"Frontend GET {path}", _test, "frontend")


def test_frontend_static_assets(frontend: str) -> None:
    def _test() -> None:
        # Load the homepage and find a _next/static asset reference
        resp = _get(f"{frontend}/")
        assert resp.status_code == 200, f"Homepage returned {resp.status_code}"
        # Find any /_next/static/ reference in the HTML
        match = re.search(r'(/_next/static/[^"\'>\s]+)', resp.text)
        assert match, "No /_next/static/ asset reference found in homepage HTML"
        asset_url = f"{frontend}{match.group(1)}"
        asset_resp = _get(asset_url)
        assert asset_resp.status_code == 200, (
            f"Static asset returned {asset_resp.status_code}: {asset_url}"
        )
    run_test("Frontend static assets (JS/CSS)", _test, "frontend")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="CTS Production E2E Tests")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--frontend-url",
        default=DEFAULT_FRONTEND_URL,
        help=f"Frontend base URL (default: {DEFAULT_FRONTEND_URL})",
    )
    parser.add_argument(
        "--json-report",
        default=None,
        help="Write JSON report to this file path",
    )
    args = parser.parse_args()

    api = args.base_url.rstrip("/")
    frontend = args.frontend_url.rstrip("/")

    print("=" * 70)
    print("  Champion Trader System -- Production E2E Tests")
    print(f"  API:      {api}")
    print(f"  Frontend: {frontend}")
    print("=" * 70)
    print()

    report.started_at = time.time()

    # --- API GET endpoints ---
    print("[API Endpoints]")
    test_root(api)
    test_health(api)
    test_scanner_latest(api)
    test_watchlist(api)
    test_trades(api)
    test_trades_stats(api)
    test_market_stance(api)
    test_alerts_unread_count(api)
    test_alerts(api)
    test_journal(api)
    test_actions(api)
    test_simulation_runs(api)
    test_intelligence_regime(api)
    test_intelligence_optimize_status(api)

    # --- API POST (calculator) ---
    print()
    print("[Calculator Validation]")
    test_calculator_position(api)

    # --- Negative tests ---
    print()
    print("[Negative Tests]")
    test_calculator_missing_fields(api)
    test_trade_not_found(api)

    # --- Frontend ---
    print()
    print("[Frontend Pages]")
    for path, contains in FRONTEND_PAGES:
        test_frontend_page(frontend, path, contains)
    test_frontend_static_assets(frontend)

    report.finished_at = time.time()

    # --- Summary ---
    print()
    print("=" * 70)
    duration = report.finished_at - report.started_at
    if report.all_passed:
        print(f"  ALL PASSED: {report.passed}/{report.total} tests "
              f"in {duration:.1f}s")
    else:
        print(f"  FAILED: {report.failed}/{report.total} tests failed "
              f"in {duration:.1f}s")
        print()
        print("  Failures:")
        for r in report.results:
            if not r.passed:
                print(f"    - {r.name}")
                for line in r.detail.splitlines()[:5]:
                    print(f"      {line}")
    print("=" * 70)

    # --- JSON report ---
    report_dict = report.to_dict()
    print()
    print(json.dumps(report_dict, indent=2))

    if args.json_report:
        with open(args.json_report, "w") as f:
            json.dump(report_dict, f, indent=2)
        print(f"\nJSON report written to: {args.json_report}")

    sys.exit(0 if report.all_passed else 1)


if __name__ == "__main__":
    main()
