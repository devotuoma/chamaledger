# Agent team

The project is built by a human lead working with a team of AI coding agents.
Each role is a working mode with a defined scope, and the output of one role is
the input of the next. The human lead owns scope and the final decision to ship.

| Role | Owns | Input | Output | Hands off to |
| --- | --- | --- | --- | --- |
| `product` | Spec, acceptance criteria, README | Project goal | `docs/spec.md`, issues | `architect` |
| `architect` | Structure, conventions, context docs | Spec | `docs/architecture.md`, `AGENTS.md` | `backend`, `frontend` |
| `backend` | API, domain rules, migrations | Issue | Code and tests in `backend/` | `qa` |
| `frontend` | User interface | Issue, API | Code and tests in `frontend/` | `qa` |
| `qa` | Test strategy and CI gates | Pull request | Passing suite or a defect report | `sre` |
| `sre` | Containers, delivery, telemetry, alerts | Merged code | `ops/`, workflows, runbooks | `on-call` |
| `on-call` | Live incidents | Alert | Fix or escalation, incident report | Human lead |

The `on-call` role runs at runtime rather than at build time: it is the
[responder service](../responder/), and it can only take allowlisted actions.

## Working agreements

- An agent works on one issue at a time and stays inside its own scope.
- A role that finds work outside its scope opens an issue instead of doing it.
- Progress is written on the issue, prefixed with the role, for example
  `[backend] claimed` or `[qa] all acceptance criteria verified`.
