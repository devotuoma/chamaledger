# Observability

## What is instrumented

The key journey is **a treasurer records a contribution**.

| Signal | Name | Store |
| --- | --- | --- |
| Metric | `chama_journey_requests_total{journey,outcome}` | Prometheus |
| Metric | `chama_journey_duration_seconds` (histogram) | Prometheus |
| Metric | `chama_probe_success` (synthetic, from the responder) | Prometheus |
| Trace | `POST /api/contributions`, `journey.record_contribution`, SQL spans | Tempo |
| Log | JSON `http_request` events with `trace_id` | Loki and stdout |

Every response carries an `X-Trace-Id` header. That ID finds the trace in Tempo
and the log lines in Loki, and each log line links to its trace in Grafana.

Run `python3 scripts/verify_telemetry.py` against a running stack to see one
request followed through all three stores.

## User interfaces

| UI | Address |
| --- | --- |
| Grafana, opens on the journey dashboard | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |

## Customer data

Names, phone numbers and notes must never reach telemetry. In layers:

1. Log fields are allowlisted in `backend/app/logs.py`.
2. Spans get only technical attributes. No bodies or headers are recorded.
3. SQL parameters are hidden, and exception text is stripped from logs.
4. The collector deletes sensitive attributes and scrubs phone patterns.

`backend/tests/integration/test_no_customer_data.py` walks the journey and searches
every span and log line. `scripts/verify_telemetry.py` checks the stored data.

**Known limitation.** A Postgres error quotes the conflicting key in its text. The
only unique customer value is the phone number, which layers 3 and 4 remove.

## Alerts

Alerts describe what users experience, and there are none for CPU or memory.

| Alert | Fires when | Who is affected |
| --- | --- | --- |
| `ContributionsFailing` | Over 5% of requests fail for 1 minute | Treasurers saving payments |
| `ContributionsSlow` | p95 is over 1 second for 1 minute | Treasurers saving payments |
| `ContributionsUnavailable` | The synthetic journey fails for 1 minute | Everyone, including in a full outage |

Rules live in `ops/prometheus/rules/journey.yml` and are unit tested by
`journey.test.yml` with `promtool`.
