# Runbook: ContributionsUnavailable

**Impact.** A synthetic contribution is failing, so real ones probably are too. If
this fires without `ContributionsFailing`, the API may be completely down.

**Triage**
1. `docker compose ps`: are `api` and `db` healthy?
2. `docker compose logs --tail 100 api`
3. If a fault flag is on, this is the same incident as `ContributionsFailing`.

**The agent** turns off an active fault flag. It has no access to restart
containers, by design, so for anything else it escalates with the evidence it
collected.

**Done when** `chama_probe_success` returns to 1 and the alert has cleared.
