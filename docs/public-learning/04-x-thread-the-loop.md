# X thread: the loop

1/ I broke my app on purpose. An agent fixed it in 1.6 minutes, with nobody touching it.

2/ Fault on. 70 seconds later the alert fires: "Treasurers cannot record contributions". No CPU graphs involved.

3/ The agent reads metrics, logs and flags, then proposes a fix. An allowlist decides if the fix may run.

4/ "Fixed" needs proof: healthy probes AND the real alert cleared. Otherwise it escalates.

5/ Code and evidence: https://github.com/devotuoma/chamaledger
