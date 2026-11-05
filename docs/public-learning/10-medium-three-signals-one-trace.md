# Medium: Following one payment through metrics, logs and traces

*How to prove your telemetry works, and that it isn't leaking customer data.*

Dashboards can look healthy while the wiring underneath is broken. So I wrote a script that proves it for ChamaLedger, a savings group ledger.

## One request, three stores

Each API response carries an `X-Trace-Id` header. The script makes a real contribution, reads that ID, and then checks three things:

1. The journey metric reached Prometheus
2. The trace reached Tempo
3. Log lines with the same trace ID reached Loki

This runs in CI against the real stack, so broken telemetry fails the build.

## The bug it would have missed without tests

FastAPI reported my route as `/contributions` instead of `/api/contributions`. My journey metric matched on the full path, so it would have stayed at zero forever, and the alert built on it would never have fired. A silent alert looks exactly like a healthy system. A test caught it.

## Keeping customer data out

Names, phone numbers and notes must never reach telemetry, so there are layers:

- Log fields come from an allowlist
- SQL parameters are hidden, and exception text is stripped from logs
- The collector deletes sensitive attributes and scrubs phone patterns

The script plants a recognisable name, note and phone number, then searches the stored data for them.

That paid off too. Tests passed on SQLite, but on Postgres the phone number appeared in the error text, because the database quotes duplicate keys itself. If you only test on SQLite, you won't see that.

Code: https://github.com/devotuoma/chamaledger
