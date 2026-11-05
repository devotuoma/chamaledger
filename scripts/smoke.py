#!/usr/bin/env python3
"""End-to-end check of the key journey through the public entry point.

usage: smoke.py BASE_URL [--read-only] [--verify-persisted MEMBER_ID]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def call(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        base + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, None


def wait_until_healthy(base, attempts=30):
    for _ in range(attempts):
        try:
            if call(base, "GET", "/api/health")[0] == 200:
                return
        except OSError:
            pass
        time.sleep(3)
    sys.exit(f"FAIL: {base} never became healthy")


def check(condition, message):
    print(("ok   " if condition else "FAIL ") + message)
    if not condition:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--verify-persisted", type=int)
    args = parser.parse_args()
    base = args.base.rstrip("/")

    wait_until_healthy(base)
    with urllib.request.urlopen(base + "/", timeout=15) as page:
        check(b"ChamaLedger" in page.read(), "frontend page is served")
    status, dashboard = call(base, "GET", "/api/dashboard")
    check(status == 200, "dashboard responds through the frontend proxy")

    if args.read_only:
        return

    if args.verify_persisted:
        _, members = call(base, "GET", "/api/members")
        check(any(m["id"] == args.verify_persisted for m in members), "data survived a restart")
        return

    stamp = int(time.time())
    status, member = call(
        base,
        "POST",
        "/api/members",
        {"full_name": "Smoke Test", "phone": f"+2567{stamp % 100_000_000:08d}"},
    )
    check(status == 201, "member created")

    payment = {
        "member_id": member["id"],
        "amount": 1000,
        "paid_on": "2026-01-01",
        "reference": f"SMOKE-{stamp}",
    }
    check(call(base, "POST", "/api/contributions", payment)[0] == 201, "contribution recorded")
    check(call(base, "POST", "/api/contributions", payment)[0] == 200, "replay is idempotent")

    _, after = call(base, "GET", "/api/dashboard")
    check(after["total_savings"] == dashboard["total_savings"] + 1000, "savings total updated")
    print(f"member_id={member['id']}")


if __name__ == "__main__":
    main()
