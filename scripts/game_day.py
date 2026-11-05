#!/usr/bin/env python3
"""Breaks the running system on purpose and requires the agent to fix it, unassisted.

usage: game_day.py {contribution_write_failure|contribution_write_latency} [--out DIR]

Exit code 0 means the whole loop worked. Nothing here helps the agent: after turning
the fault on, this script only watches.
"""

import argparse
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "http://localhost:8080/api"
PROMETHEUS = "http://localhost:9090"
RESPONDER = "http://localhost:8100"
OPS_HEADERS = {"X-Ops-Token": "local-ops-token", "Content-Type": "application/json"}
EXPECTED_ALERTS = {
    "contribution_write_failure": {"ContributionsFailing", "ContributionsUnavailable"},
    "contribution_write_latency": {"ContributionsSlow"},
}
TIMEOUT_SECONDS = 600


def http(method, url, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url, data=data, method=method, headers=headers or {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.load(response)


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def fail(message):
    sys.exit(f"GAME DAY FAILED: {message}")


def firing_alerts():
    query = urllib.parse.urlencode({"query": 'ALERTS{alertstate="firing"}'})
    _, body = http("GET", f"{PROMETHEUS}/api/v1/query?{query}")
    return {series["metric"]["alertname"] for series in body["data"]["result"]}


def real_contribution_works():
    phone = f"+2565{random.randrange(10**8):08d}"
    _, member = http("POST", f"{API}/members", {"full_name": "Game Day", "phone": phone})
    status, _ = http(
        "POST",
        f"{API}/contributions",
        {
            "member_id": member["id"],
            "amount": 100,
            "paid_on": "2026-01-01",
            "reference": f"GAMEDAY-{random.randrange(10**12)}",
        },
    )
    return status == 201


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fault", choices=sorted(EXPECTED_ALERTS))
    parser.add_argument("--out", default="game-day-report")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if not real_contribution_works():
        fail("the journey was not healthy before the fault")
    log("Journey is healthy. Injecting the fault.")
    http("PUT", f"{API}/ops/flags/{args.fault}", {"enabled": True}, OPS_HEADERS)
    injected = time.time()

    incident = None
    fired = False
    deadline = injected + TIMEOUT_SECONDS
    while time.time() < deadline:
        firing = firing_alerts()
        if firing & EXPECTED_ALERTS[args.fault] and not fired:
            fired = True
            log(f"Alert fired after {time.time() - injected:.0f}s: {sorted(firing)}")
        _, incidents = http("GET", f"{RESPONDER}/incidents")
        if incidents and incident is None:
            log(f"Agent woke: {incidents[0]['id']} for {incidents[0]['alert_name']}")
        incident = incidents[0] if incidents else None
        if incident and incident["status"] != "investigating":
            break
        time.sleep(5)
    else:
        fail(f"no finished incident within {TIMEOUT_SECONDS}s (alert fired: {fired})")

    recovered = time.time()
    (out / f"{incident['id']}.json").write_text(json.dumps(incident, indent=2))
    for entry in incident["timeline"]:
        log(f"  agent: {entry['message']}")

    if incident["status"] != "resolved":
        fail(f"the agent ended with status {incident['status']}")
    if incident["plan"]["target"] != args.fault:
        fail(f"the agent acted on {incident['plan']['target']}")
    if incident["alert_name"] not in EXPECTED_ALERTS[args.fault]:
        fail(f"woken by an unexpected alert: {incident['alert_name']}")
    _, flags = http("GET", f"{API}/ops/flags", headers=OPS_HEADERS)
    if flags[args.fault]:
        fail("the fault flag is still on")
    if not real_contribution_works():
        fail("a real contribution still fails after the incident")

    summary = {
        "fault": args.fault,
        "incident": incident["id"],
        "alert": incident["alert_name"],
        "status": incident["status"],
        "minutes_from_fault_to_verified_recovery": round((recovered - injected) / 60, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    log(f"PASSED {json.dumps(summary)}")


if __name__ == "__main__":
    main()
