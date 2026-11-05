# Deployment

```text
merge to main -> CI passes -> images published (tagged by SHA) -> dev deploy -> smoke test
                                                                                  |
                 manual "Deploy to production" (needs approval) <-----------------+
```

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `ci.yml` | Every pull request and push | Lint, all tests, and the full stack in Docker |
| `cd.yml` | CI passing on `main` | Publishes images, deploys to **dev**, runs the smoke test |
| `deploy-production.yml` | Manual, with reviewer approval | Deploys a chosen SHA to **production** |
| `rollback.yml` | Manual | Restores any earlier SHA in either environment |

## Rollback

There are two paths:

- **Automatic.** If a new release fails its smoke test, the deploy workflow restores the
  release tagged `<environment>-current` and confirms that it is live. That tag moves
  only after a smoke test passes, so it always names the last good release.
- **Manual.** Run **Roll back** with an environment and an earlier SHA.

Rollback swaps containers and does not reverse migrations, so **migrations must be
additive**: add new columns and tables, and remove old ones only in a later release,
once no running version uses them. The previous version then keeps working on the
newer schema.

## Hosting setup

The app runs on [Render](https://render.com) free web services, with Postgres on
[Neon](https://neon.tech). Neither needs a card.

1. In Neon, create a project with databases `dev` and `prod`. Copy both connection strings.
2. In Render, choose **New > Blueprint** and select this repository.
3. Enter the values Render asks for: `DATABASE_URL` for each API, and `API_URL` for each
   web service (the `https://` address of its API).
4. Copy each service's **Deploy Hook** from its settings, then:

```bash
gh secret set API_DEPLOY_HOOK --env dev
gh secret set FRONTEND_DEPLOY_HOOK --env dev
gh secret set API_DEPLOY_HOOK --env production
gh secret set FRONTEND_DEPLOY_HOOK --env production
gh variable set APP_URL --env dev --body https://chamaledger-web-dev.onrender.com
gh variable set APP_URL --env production --body https://chamaledger-web-prod.onrender.com
```

Until these exist, CD still publishes images but reports that nothing was deployed.

## Differences from the local stack

- `CHAOS_ENABLED` and `OPS_TOKEN` are unset, so the ops API returns 404 and fault flags
  have no effect.
- `OTEL_ENABLED` is unset because free hosting runs no collector, so hosted environments
  emit JSON logs to stdout only. The full telemetry stack, alerts and on-call agent run
  in Compose and in the game day workflow.
- Free services sleep when idle, so the first request after a pause can take about a minute.
- There is no authentication in v1, so hosted environments are for demo data only.
