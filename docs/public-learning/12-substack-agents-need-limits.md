# Substack: Give your agents less power than you think

When I set out to build an on-call agent, I pictured something that could do anything: restart containers, roll back releases, edit config.

The version that shipped can do one thing: turn off a known fault flag.

It has no shell, no Docker socket and no database access. Whatever its planner proposes passes through an allowlist first, and anything else goes to a human with the evidence attached.

That sounds disappointing, but here is what it gave me:

- **I can reason about the worst case.** The most damage it can do is turn off a fault flag.
- **Prompt injection has little to grab.** If an LLM planner is enabled, text in the evidence can't widen what's allowed. It also only sees technical facts, with no log text or customer data.
- **Escalation is a real outcome.** It isn't the agent giving up. Most real outages should end with a person holding a clear report.

I'd rather extend trust one tested action at a time than remove limits after an incident.

The agent, and the honest list of what it doesn't prove: https://github.com/devotuoma/chamaledger/blob/main/responder/README.md
