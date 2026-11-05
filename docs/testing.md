# Testing

Run everything with one command:

```bash
make setup   # first time only; needs Python 3.12+ and Node 22+
make test
```

| Layer | Location | What it proves |
| --- | --- | --- |
| Unit | `backend/tests/unit` | Pure rules: interest, loan limits, PAR30 |
| Integration | `backend/tests/integration` | API plus a real database, built by the real migrations |
| Frontend | `frontend/tests` | Views, forms and error handling in jsdom |
| Stack smoke | `scripts/smoke.py` | The running containers work end to end, through nginx |
| Game day | `.github/workflows/game-day.yml` | A real fault is alerted on and fixed by the agent |

Integration tests use a temporary SQLite file by default. To run them against
Postgres, as CI does:

```bash
TEST_DATABASE_URL=postgresql://user:pass@localhost/db make test-backend
```

## Requirement traceability

Test names include the acceptance criterion they cover, for example
`test_ac_2_2_replay_returns_the_original_and_creates_nothing`.

| Requirement | Tests |
| --- | --- |
| FR-1 Members | `tests/integration/test_members.py` |
| FR-2 Contributions | `tests/integration/test_contributions.py`, `frontend/tests/contributions.test.js` |
| FR-3 Loans | `tests/unit/test_domain.py`, `tests/integration/test_loans.py` |
| FR-4 Repayments | `tests/integration/test_loans.py`, `frontend/tests/loans.test.js` |
| FR-5 Dashboard | `tests/unit/test_domain.py`, `tests/integration/test_dashboard.py` |
