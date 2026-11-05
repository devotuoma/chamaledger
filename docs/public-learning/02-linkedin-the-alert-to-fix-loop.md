# LinkedIn: the alert-to-fix loop

I broke my own app on purpose, and it fixed itself in 1.6 minutes.

What happened with no human involved:

1. A fault made saving contributions fail
2. A real alert fired, worded as user impact: "Treasurers cannot record contributions"
3. An on-call agent woke up and read metrics, logs and flags
4. It turned off the faulty flag
5. It only called the incident resolved after the journey worked and the alert cleared

My favourite part is the run where it failed. A bug stopped its fix, and it escalated to a human instead of claiming success.

An agent that admits it failed is worth more than one that always says it succeeded.

Repo and evidence: https://github.com/devotuoma/chamaledger/blob/main/docs/evidence/game-day.md

#SRE #AIAgents #Observability
