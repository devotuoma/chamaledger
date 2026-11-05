# Runbook: ContributionsFailing

**Impact.** Treasurers see an error when saving a contribution. Payments may go
unrecorded until they retry. A retry is safe because references are idempotent.

**Triage**
1. Open the Grafana journey dashboard (http://localhost:3000) and confirm the drop.
2. Find failed requests in the logs panel. `error_type` names the failure.
3. Follow `TraceID` on a failed line to see which step failed.

| `error_type` | Likely cause | Fix |
| --- | --- | --- |
| `ContributionWriteFault` | The `contribution_write_failure` flag is on | Turn the flag off |
| `OperationalError` | Database unreachable or out of connections | Check `db`, then escalate |
| Anything else | A bad release | Run the rollback workflow, see [deployment](../deployment.md) |

**The agent** handles the first row by itself and escalates the others.

**Done when** the alert has cleared and a real contribution saves successfully.
