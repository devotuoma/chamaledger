# Architecture

```text
 Browser -> frontend (nginx) -> /api -> backend (FastAPI) -> Postgres
                                           | OTLP
                                           v
                                    otel-collector
                              /            |           \
                         Prometheus       Loki        Tempo
                              |             \           /
                         Alertmanager        Grafana (UI)
                              | webhook
                              v
                     responder (on-call agent) -> ops API on the backend
```

| Component | Path | Purpose |
| --- | --- | --- |
| Backend | `backend/` | REST API, domain rules, migrations |
| Frontend | `frontend/` | Static ES modules served by nginx, which proxies `/api` |
| Responder | `responder/` | On-call agent woken by Alertmanager |
| Operations | `ops/` | Telemetry stack configuration and alert rules |

## Key decisions

- **Integer money.** Amounts are whole integers, so rounding cannot move money.
- **Idempotency by reference.** Each payment has a unique external reference, so
  a retry over a bad mobile connection cannot record it twice.
- **Database-enforced invariants.** Unique constraints and a partial unique index
  hold under concurrent requests, where application checks alone would not.
- **No frontend build step.** There is less to break, and no bundle to maintain.
- **Alert on the journey.** Alerts describe what treasurers experience, not
  server resource usage.
