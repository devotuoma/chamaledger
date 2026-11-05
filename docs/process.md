# Process

```text
issue -> claim -> branch -> small commits -> pull request -> CI -> merge -> deploy to dev
```

1. **Specify.** `product` writes an issue with testable acceptance criteria.
2. **Claim.** The owning agent comments `[role] claimed` on the issue.
3. **Build.** Work happens on a branch named `<type>/<issue>-<slug>`, one logical
   change per commit.
4. **Verify.** `make test` passes locally. The pull request says `Closes #n`.
5. **Gate.** CI must pass before merge. `qa` confirms each acceptance criterion
   on the issue.
6. **Release.** Merging deploys to dev. Production is a manual, gated workflow.
7. **Learn.** Incident reports feed new issues and runbook updates.

The public tracker is
[GitHub Issues](https://github.com/devotuoma/chamaledger/issues), grouped into
[milestones](https://github.com/devotuoma/chamaledger/milestones).

Pull requests are merged with merge commits so the small steps stay readable.
