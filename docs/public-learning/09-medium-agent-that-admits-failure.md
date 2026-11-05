# Medium: The most useful thing my on-call agent did was fail

*Building an agent that wakes on a real alert, fixes what it safely can, and says so when it can't.*

For my final project I built ChamaLedger, a ledger for savings groups. The brief said to alert on real user impact and implement a responder agent. Here is how that went, and why the failed run taught me the most.

## Start from the user, not the server

The key journey is one sentence: a treasurer records a contribution. Everything hangs off it. The three alerts read like complaints from a user:

- **ContributionsFailing:** over 5% of requests fail
- **ContributionsSlow:** p95 is over one second
- **ContributionsUnavailable:** a synthetic contribution fails

The third one exists because of a gap. If the API is completely down, it can't report its own errors, so an error-rate alert stays silent during the worst possible outage. A probe from outside closes that gap.

## The agent's loop

```text
alert -> investigate -> plan -> enforce allowlist -> act -> verify -> report
```

The important design choice is that the allowlist sits *outside* the planner. A deterministic runbook or an optional LLM can propose whatever it likes, but only "disable a known fault that is currently on" can run. Anything else becomes an escalation. The agent has no shell, no Docker socket and no database credentials.

## "Fixed" has to be proven

An agent that reports success because its action returned 200 is worse than no agent. This one needs consecutive healthy probes *and* the real alert cleared in Prometheus. If that doesn't happen in time, it escalates.

## The failed run

The first game day failed. The alert fired in about 70 seconds and the diagnosis was right, but the fix returned an error: I had sent JSON without a Content-Type header, and my fake test tools had hidden that.

The agent escalated, with its evidence, and the game day failed as it should. I fixed the bug and added tests for the real HTTP layer.

After that, both scenarios passed with no human input: 1.6 minutes from fault to verified recovery for failures, 3.3 minutes for latency.

## What this doesn't prove

The faults are injected, and the agent's scope is narrow. A real outage would mostly end in an escalation with a good evidence pack, and I think that's the right default.

Code, game day evidence and the incident reports the agent filed: https://github.com/devotuoma/chamaledger
