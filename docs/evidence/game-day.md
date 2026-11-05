# Game day evidence

The [game day workflow](../../.github/workflows/game-day.yml) starts the full system,
turns on a fault and then only watches. It fails unless the real alert fires, the agent
fixes the fault by itself, and a real contribution works afterwards.

## Result on `main`

[Run 42011396858](https://github.com/devotuoma/chamaledger/actions/runs/42011396858)

| Fault | Alert that woke the agent | Agent's action | Fault to verified recovery | Incident filed by the agent |
| --- | --- | --- | --- | --- |
| `contribution_write_failure` | `ContributionsUnavailable` | Disabled the flag | 1.6 minutes | [#46](https://github.com/devotuoma/chamaledger/issues/46) |
| `contribution_write_latency` | `ContributionsSlow` | Disabled the flag | 3.3 minutes | [#47](https://github.com/devotuoma/chamaledger/issues/47) |

The alert took 70 to 80 seconds to fire in the runs inspected. Recovery takes longer for
latency because the agent waits for the real alert to clear, and that alert reads a
two-minute window.

## What it looks like

From an earlier run of the same scenario, on [PR #44](https://github.com/devotuoma/chamaledger/pull/44):

```text
Journey is healthy. Injecting the fault.
Alert fired after 70s: ['ContributionsUnavailable']
Agent woke: INC-ba44181f for ContributionsUnavailable
  agent: Investigated: error ratio 1.0, p95 0.0475, flags ['contribution_write_failure'], errors {'ContributionWriteFault': 14}
  agent: Plan from runbook: disable_fault contribution_write_failure.
  agent: Disabled contribution_write_failure, verifying recovery
  agent: 3 consecutive probes healthy, waiting for the alert
  agent: Recovery verified: journey healthy and alert cleared
PASSED
```

## The safety path, proven by accident

In [the first run](https://github.com/devotuoma/chamaledger/actions/runs/42009901889) the
agent's fix failed because of a real bug in its own request. It did not claim success. It
escalated with its evidence, and the game day failed as it should. The bug got a regression
test in `responder/tests/test_tools.py`.

## What this does not prove

- The agent's real-world scope is narrow. It fixes flag-based faults and escalates
  everything else, by design.
- The faults are injected. A real outage would mostly end in an escalation.
- The LLM planner was tested against a mocked endpoint only. All of these runs used the
  deterministic runbook planner.
