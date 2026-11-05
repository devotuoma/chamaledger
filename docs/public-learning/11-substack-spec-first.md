# Substack: What writing the spec first changed

I've started plenty of projects by opening an editor. This time, the first commit was a spec.

ChamaLedger is a ledger for savings groups. Before any code, each requirement got a number and testable acceptance criteria. For example:

> AC-2.2 Replaying the same reference with the same data returns the original record with 200 and creates nothing.

Three things changed.

**Work got smaller.** Each task became a GitHub issue with checkboxes, handled by one role in a small team of AI coding agents, with progress written on the issue. I could review a claim against a sentence rather than a feeling.

**Tests wrote themselves, more or less.** That criterion became a test called `test_ac_2_2_replay_returns_the_original_and_creates_nothing`. When it fails, the name tells you which promise broke.

**The hard questions came early.** "What happens if the same reference arrives with a different amount?" is a two-minute decision in a spec. In production, it's money in the wrong place.

It didn't stop me making mistakes. Early on, a batch script merged two pull requests while a test was failing. The test itself turned out to be wrong, but the process was too. I logged it as a tracked issue and made CI a required check on `main`.

A spec doesn't make you right. It gives you something definite to be wrong about.

The spec and tracker are public: https://github.com/devotuoma/chamaledger/blob/main/docs/spec.md
