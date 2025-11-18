#!/usr/bin/env python3
"""Simple API smoke test for DirectTorrent.me JSON endpoints.

Run locally with:
    python tools/check_api.py --base https://your-backend.herokuapp.com \
        --email demo@example.com --password hunter2
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

import requests


class ApiClient:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> requests.Response:
        url = f"{self.base}{path}"
        response = self.session.request(method, url, json=payload, timeout=20)
        return response

    def get_me(self) -> Dict[str, Any]:
        res = self._request("GET", "/api/auth/me")
        res.raise_for_status()
        return res.json()

    def login(self, email_or_username: str, password: str) -> Dict[str, Any]:
        res = self._request(
            "POST",
            "/api/auth/login",
            {"email_or_username": email_or_username, "password": password},
        )
        res.raise_for_status()
        return res.json()

    def list_torrents(self) -> Dict[str, Any]:
        res = self._request("GET", "/api/torrents")
        res.raise_for_status()
        return res.json()

    def admin_overview(self) -> Dict[str, Any]:
        res = self._request("GET", "/api/admin/overview")
        res.raise_for_status()
        return res.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="DirectTorrent.me API smoke tester")
    parser.add_argument("--base", default="http://localhost:5000", help="API base URL, e.g., https://directtorrent-backend.herokuapp.com")
    parser.add_argument("--email", help="User email for login (optional)")
    parser.add_argument("--password", help="User password for login (optional)")
    parser.add_argument("--admin", action="store_true", help="Also hit admin overview when authenticated as admin")
    args = parser.parse_args()

    client = ApiClient(args.base)

    def print_result(label: str, payload: Dict[str, Any]) -> None:
        print(f"\n=== {label} ===")
        print(json.dumps(payload, indent=2, sort_keys=True))

    try:
        print_result("GET /api/auth/me (unauthenticated)", client.get_me())
    except Exception as exc:  # noqa: BLE001
        print(f"[error] /api/auth/me failed: {exc}")
        return 1

    if args.email and args.password:
        try:
            login_payload = client.login(args.email, args.password)
            print_result("POST /api/auth/login", login_payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] login failed: {exc}")
            return 1
    else:
        print("\n[info] Skipping login (no --email/--password provided)")

    try:
        print_result("GET /api/torrents", client.list_torrents())
    except Exception as exc:  # noqa: BLE001
        print(f"[error] listing torrents failed: {exc}")
        return 1

    if args.admin and args.email and args.password:
        try:
            print_result("GET /api/admin/overview", client.admin_overview())
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] admin overview failed (requires admin account): {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
