# Responder: the on-call agent

Alertmanager wakes this service through a webhook. It then runs one loop:

```text
alert -> investigate -> plan -> enforce allowlist -> act -> verify -> report
```

| Step | What happens |
| --- | --- |
| Investigate | Reads the error ratio and p95 (Prometheus), failed requests and traces (Loki), and fault flags (ops API). A missing source is recorded as a gap, and the investigation continues. |
| Plan | The runbook planner maps alert and evidence to an action. If `LLM_BASE_URL` and `LLM_MODEL` are set, an LLM plans first, and the runbook is the fallback. |
| Allowlist | Whichever planner ran, only disabling a known fault that is currently on can execute. Everything else becomes an escalation. |
| Act | Turns the flag off through the token-protected ops API. |
| Verify | Needs consecutive healthy probes **and** the real alert cleared. If that does not happen in time, it escalates rather than claiming success. |
| Report | Writes Markdown and JSON, available at `GET /incidents`, and files a GitHub issue when configured. |

## Safety

- It has no shell, no Docker socket and no database credentials. `tools.py` is its
  complete reach.
- Only technical facts go to an LLM (`Evidence.summary`): no log text and no customer
  data. Its output cannot widen the allowlist, which limits prompt injection.
- The webhook requires a bearer token.

## LLM planner status

The runbook planner is the one proven in the game day. The LLM planner is covered by
tests against a mocked endpoint, and has **not** been run against a real provider.
