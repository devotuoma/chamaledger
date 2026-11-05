"""Pure business rules. Nothing here touches the database or the network."""

from dataclasses import dataclass
from datetime import date

LOAN_TO_SAVINGS_MULTIPLE = 3
PAR_DAYS = 30
BPS = 10_000


def total_due(principal: int, interest_rate_bps: int) -> int:
    """Flat interest, rounded down so that rounding never overcharges a member."""
    return principal + principal * interest_rate_bps // BPS


def max_loan(savings: int) -> int:
    return savings * LOAN_TO_SAVINGS_MULTIPLE


def is_past_due_for_par(due_on: date, as_of: date, days: int = PAR_DAYS) -> bool:
    return (as_of - due_on).days > days


@dataclass(frozen=True)
class OpenLoan:
    due_on: date
    outstanding: int


def portfolio_at_risk(loans: list[OpenLoan], as_of: date, days: int = PAR_DAYS) -> float:
    """Share of outstanding balance on loans more than `days` late, between 0 and 1."""
    total = sum(loan.outstanding for loan in loans)
    if total == 0:
        return 0.0
    at_risk = sum(
        loan.outstanding for loan in loans if is_past_due_for_par(loan.due_on, as_of, days)
    )
    return at_risk / total
