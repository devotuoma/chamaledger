# Runbook: ContributionsSlow

**Impact.** Saving takes over a second for at least 5% of requests. Treasurers on
poor connections may resubmit or give up.

**Triage**
1. Check p95 on the Grafana journey dashboard.
2. Open a slow trace in Tempo. Compare database spans with total duration.

| Observation | Likely cause | Fix |
| --- | --- | --- |
| `contribution_write_latency` flag on | Injected fault | Turn the flag off |
| Long database spans | Lock contention or a missing index | Investigate, then escalate |
| Short spans, long request | Connection pool wait | Check pool use, then escalate |

**The agent** handles the first row by itself and escalates the others.

**Done when** the alert has cleared.
