from datetime import date

import pytest

from app.domain import OpenLoan, is_past_due_for_par, max_loan, portfolio_at_risk, total_due

AS_OF = date(2026, 6, 30)


@pytest.mark.parametrize(
    ("principal", "bps", "expected"),
    [(100_000, 1000, 110_000), (100_000, 0, 100_000), (999, 1000, 1098), (1, 1000, 1)],
)
def test_ac_3_3_flat_interest_rounds_down(principal, bps, expected):
    assert total_due(principal, bps) == expected


def test_ac_3_1_loan_cap_is_three_times_savings():
    assert max_loan(50_000) == 150_000
    assert max_loan(0) == 0


@pytest.mark.parametrize(
    ("due_on", "expected"),
    [(date(2026, 5, 31), False), (date(2026, 5, 30), False), (date(2026, 5, 29), True)],
)
def test_ac_5_2_par_counts_strictly_more_than_30_days(due_on, expected):
    assert (AS_OF - due_on).days in (30, 31, 32)
    assert is_past_due_for_par(due_on, AS_OF) is expected


def test_ac_5_2_par_is_the_late_share_of_outstanding():
    loans = [
        OpenLoan(due_on=date(2026, 1, 1), outstanding=25_000),
        OpenLoan(due_on=date(2026, 7, 1), outstanding=75_000),
    ]
    assert portfolio_at_risk(loans, AS_OF) == 0.25


def test_ac_5_3_par_of_an_empty_portfolio_is_zero():
    assert portfolio_at_risk([], AS_OF) == 0.0
