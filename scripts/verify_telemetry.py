#!/usr/bin/env python3
"""Follows one real request across metrics, logs and traces, and looks for leaked customer data.

usage: verify_telemetry.py [--base URL] [--prometheus URL] [--loki URL] [--tempo URL]
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

SECRET_NAME = "Verify Secretperson"
SECRET_NOTE = "verify-secret-note"


def post(url, body):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.headers, json.load(response)


def get(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.load(response)


def eventually(description, probe, timeout=90):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            result = probe()
            if result:
                print(f"ok   {description}")
                return result
        except Exception as error:  # noqa: BLE001 (the stores may still be starting)
            last_error = error
        time.sleep(3)
    sys.exit(f"FAIL {description} (last error: {last_error})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8080")
    parser.add_argument("--prometheus", default="http://localhost:9090")
    parser.add_argument("--loki", default="http://localhost:3100")
    parser.add_argument("--tempo", default="http://localhost:3200")
    args = parser.parse_args()

    stamp = int(time.time())
    phone = f"+2567{stamp % 100_000_000:08d}"
    _, member = post(f"{args.base}/api/members", {"full_name": SECRET_NAME, "phone": phone})
    headers, _ = post(
        f"{args.base}/api/contributions",
        {
            "member_id": member["id"],
            "amount": 700,
            "paid_on": "2026-01-01",
            "reference": f"VERIFY-{stamp}",
            "note": SECRET_NOTE,
        },
    )
    trace_id = headers["X-Trace-Id"]
    print(f"trace_id={trace_id}")

    query = urllib.parse.urlencode(
        {"query": 'sum(chama_journey_requests_total{journey="record_contribution"})'}
    )
    eventually(
        "metrics reached Prometheus",
        lambda: get(f"{args.prometheus}/api/v1/query?{query}")["data"]["result"],
    )

    def trace_found():
        batches = get(f"{args.tempo}/api/traces/{trace_id}")
        text = json.dumps(batches)
        return "journey.record_contribution" in text and text

    trace_text = eventually("the request's trace reached Tempo", trace_found)

    def logs_found():
        params = urllib.parse.urlencode(
            {
                "query": f'{{service_name="chamaledger-api"}} | trace_id="{trace_id}"',
                "start": str((stamp - 300) * 10**9),
                "limit": "50",
            }
        )
        streams = get(f"{args.loki}/loki/api/v1/query_range?{params}")["data"]["result"]
        return streams and json.dumps(streams)

    log_text = eventually("the same trace ID is on logs in Loki", logs_found)

    def all_logs():
        params = urllib.parse.urlencode(
            {
                "query": '{service_name="chamaledger-api"}',
                "start": str((stamp - 300) * 10**9),
                "limit": "1000",
            }
        )
        return json.dumps(get(f"{args.loki}/loki/api/v1/query_range?{params}"))

    everything = trace_text + log_text + all_logs()
    for secret in (SECRET_NAME, SECRET_NOTE, phone):
        if secret in everything:
            sys.exit(f"FAIL customer data reached telemetry: {secret}")
    print("ok   no customer data in the stored logs or this trace")


if __name__ == "__main__":
    main()
