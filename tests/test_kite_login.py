"""Tests for the daily Kite login helpers — pure auth logic (no network).

Covers the session checksum, the request_token -> access_token exchange (injected transport),
the failure path, and the .env KITE_ACCESS_TOKEN rewrite used by scripts/kite_login.py."""
import hashlib
import importlib.util

import pytest

from backend.engine.kite_data import exchange_request_token, login_url, session_checksum


def _load_kite_login():
    spec = importlib.util.spec_from_file_location(
        "kite_login", "/home/user/champion-trader/scripts/kite_login.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_session_checksum_is_sha256_of_concatenation():
    expected = hashlib.sha256(b"akreqtoksecret").hexdigest()
    assert session_checksum("ak", "reqtok", "secret") == expected


def test_login_url_carries_the_api_key():
    assert "api_key=AK123" in login_url("AK123")


def test_exchange_request_token_parses_and_signs():
    captured = {}

    def fake_post(url, fields):
        captured["url"], captured["fields"] = url, fields
        return b'{"status":"success","data":{"access_token":"TOKEN123"}}'

    tok = exchange_request_token("ak", "secret", "reqtok", http_post=fake_post)
    assert tok == "TOKEN123"
    assert captured["url"].endswith("/session/token")
    assert captured["fields"]["checksum"] == session_checksum("ak", "reqtok", "secret")


def test_exchange_request_token_raises_on_error_payload():
    def fake_post(url, fields):
        return b'{"status":"error","message":"token expired"}'

    with pytest.raises(RuntimeError):
        exchange_request_token("ak", "secret", "bad", http_post=fake_post)


def test_set_env_var_replaces_existing_line():
    mod = _load_kite_login()
    text = "KITE_API_KEY=ak\nKITE_ACCESS_TOKEN=old\nTELEGRAM_CHAT_ID=1\n"
    out = mod.set_env_var(text, "KITE_ACCESS_TOKEN", "new")
    assert "KITE_ACCESS_TOKEN=new" in out and "old" not in out
    assert "KITE_API_KEY=ak" in out and "TELEGRAM_CHAT_ID=1" in out   # others preserved


def test_set_env_var_appends_when_absent():
    mod = _load_kite_login()
    out = mod.set_env_var("KITE_API_KEY=ak\n", "KITE_ACCESS_TOKEN", "tok")
    assert out.endswith("KITE_ACCESS_TOKEN=tok\n") and "KITE_API_KEY=ak" in out
