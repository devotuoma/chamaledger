# AGENTS.md

ChamaLedger is a ledger for savings groups: FastAPI, Postgres and a static
JavaScript frontend, with OpenTelemetry telemetry and an on-call responder agent.

Read this first, then only the document your task needs.

| Need | Read |
| --- | --- |
| What to build and why | [docs/spec.md](docs/spec.md) |
| Which role you are and who you hand off to | [docs/team.md](docs/team.md) |
| How work moves from issue to merge | [docs/process.md](docs/process.md) |
| Components and data flow | [docs/architecture.md](docs/architecture.md) |
| Running the tests | [docs/testing.md](docs/testing.md) |
| Deploying and rolling back | [docs/deployment.md](docs/deployment.md) |
| Signals, dashboards and alerts | [docs/observability.md](docs/observability.md) |
| Responding to an alert | [docs/runbooks/](docs/runbooks/) |

## Rules that always apply

- `make test` must pass before a pull request is opened.
- Money is stored as whole integers. Never use floats for amounts.
- Never add names, phone numbers or notes to logs, spans or metric labels.
- Migrations are additive so that a rollback stays safe.
- Every change traces to an issue with acceptance criteria.
