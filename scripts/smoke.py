#!/usr/bin/env python3
"""End-to-end check of the key journey through the public entry point.

usage: smoke.py BASE_URL [--read-only] [--verify-persisted MEMBER_ID] [--expect-version SHA]
"""

import argparse
import json
import random
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


def wait_for_version(base, version, attempts=60):
    """A deploy takes a while to go live, and the old version answers until it does."""
    current = None
    for _ in range(attempts):
        try:
            status, body = call(base, "GET", "/api/health")
            current = body and body.get("version")
            if status == 200 and current == version:
                print(f"ok   version {version} is live")
                return
        except OSError:
            pass
        time.sleep(10)
    sys.exit(f"FAIL: version {version} never went live (still seeing {current})")


def check(condition, message):
    print(("ok   " if condition else "FAIL ") + message)
    if not condition:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--verify-persisted", type=int)
    parser.add_argument("--expect-version")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    wait_until_healthy(base)
    if args.expect_version:
        wait_for_version(base, args.expect_version)
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
        {"full_name": "Smoke Test", "phone": f"+2567{random.randrange(10**8):08d}"},
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
