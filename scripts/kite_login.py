"""Daily Kite login — exchange a request_token for today's access_token and store it.

Kite Connect access tokens expire every morning, so this runs once a day before the 17:30
ingest (Zerodha does not allow fully-unattended tokens; the login itself is interactive).

    # 1. print the login URL, open it, log in -> you're redirected to
    #    <your-redirect-url>?request_token=XXXX&status=success
    python scripts/kite_login.py

    # 2. paste the request_token back -> writes KITE_ACCESS_TOKEN into .env
    python scripts/kite_login.py --request-token XXXX

Reads KITE_API_KEY / KITE_API_SECRET from .env. Pure auth logic lives in
backend/engine/kite_data.py (login_url / session_checksum / exchange_request_token).
"""
import argparse
import re
import sys

sys.path.insert(0, "/home/user/champion-trader")
from backend.engine.kite_data import exchange_request_token, login_url   # noqa: E402

ROOT = "/home/user/champion-trader"
ENV_PATH = f"{ROOT}/.env"


def _read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in open(ENV_PATH):
        s = line.strip()
        if "=" in s and not s.startswith("#"):
            k, v = s.split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
    return env


def set_env_var(text: str, key: str, value: str) -> str:
    """Return `text` with KEY=value replaced (or appended if absent). Pure — unit-tested."""
    line = f"{key}={value}"
    if re.search(rf"(?m)^{re.escape(key)}=.*$", text):
        return re.sub(rf"(?m)^{re.escape(key)}=.*$", line, text)
    return text.rstrip("\n") + f"\n{line}\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request-token", help="the request_token from the post-login redirect URL")
    args = ap.parse_args()

    env = _read_env()
    api_key, api_secret = env.get("KITE_API_KEY", ""), env.get("KITE_API_SECRET", "")
    if not api_key or not api_secret:
        sys.exit("ERROR: set KITE_API_KEY and KITE_API_SECRET in .env first.")

    if not args.request_token:
        print("1) Open this URL, log in to Zerodha:\n")
        print(f"   {login_url(api_key)}\n")
        print("2) You'll be redirected to <redirect-url>?request_token=XXXX&status=success")
        print("3) Re-run:  python scripts/kite_login.py --request-token XXXX")
        return

    access_token = exchange_request_token(api_key, api_secret, args.request_token)
    with open(ENV_PATH) as fh:
        updated = set_env_var(fh.read(), "KITE_ACCESS_TOKEN", access_token)
    with open(ENV_PATH, "w") as fh:
        fh.write(updated)
    print(f"OK: KITE_ACCESS_TOKEN refreshed (…{access_token[-6:]}). Ready for today's ingest.")


if __name__ == "__main__":
    main()
