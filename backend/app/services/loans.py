from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import max_loan, total_due
from app.errors import Conflict, NotFound
from app.models import Loan, Repayment
from app.schemas import LoanCreate, LoanOut, RepaymentCreate
from app.services.members import get_member, savings_of


def outstanding_of(loan: Loan) -> int:
    paid = sum(repayment.amount for repayment in loan.repayments)
    return total_due(loan.principal, loan.interest_rate_bps) - paid


def to_out(loan: Loan, as_of: date) -> LoanOut:
    outstanding = outstanding_of(loan)
    days_late = max((as_of - loan.due_on).days, 0) if loan.closed_on is None else 0
    return LoanOut(
        id=loan.id,
        member_id=loan.member_id,
        principal=loan.principal,
        interest_rate_bps=loan.interest_rate_bps,
        issued_on=loan.issued_on,
        due_on=loan.due_on,
        closed_on=loan.closed_on,
        total_due=total_due(loan.principal, loan.interest_rate_bps),
        outstanding=outstanding,
        days_late=days_late,
    )


def issue_loan(session: Session, data: LoanCreate) -> Loan:
    member = get_member(session, data.member_id)
    if not member.active:
        raise Conflict("This member is inactive and cannot borrow")
    limit = max_loan(savings_of(session, member.id))
    if data.principal > limit:
        raise Conflict(f"Principal exceeds this member's limit of {limit}")

    loan = Loan(**data.model_dump())
    session.add(loan)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise Conflict("This member already has an open loan") from exc
    return loan


def list_loans(session: Session) -> list[Loan]:
    return list(session.scalars(select(Loan).order_by(Loan.id.desc())))


def open_loans(session: Session) -> list[Loan]:
    return list(session.scalars(select(Loan).where(Loan.closed_on.is_(None))))


def _replay(existing: Repayment, loan_id: int, data: RepaymentCreate) -> None:
    same = (
        existing.loan_id == loan_id
        and existing.amount == data.amount
        and existing.paid_on == data.paid_on
    )
    if not same:
        raise Conflict(f"Reference {data.reference} was already used for a different payment")


def record_repayment(
    session: Session, loan_id: int, data: RepaymentCreate
) -> tuple[Loan, bool]:
    """Returns the loan and whether this call created a repayment."""
    # Lock the loan so that concurrent repayments cannot both pass the balance check.
    loan = session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    if loan is None:
        raise NotFound(f"Loan {loan_id} not found")

    existing = session.scalar(select(Repayment).where(Repayment.reference == data.reference))
    if existing is not None:
        _replay(existing, loan_id, data)
        return loan, False

    outstanding = outstanding_of(loan)
    if data.amount > outstanding:
        raise Conflict(f"Repayment exceeds the outstanding balance of {outstanding}")

    session.add(Repayment(loan_id=loan_id, **data.model_dump()))
    if data.amount == outstanding:
        loan.closed_on = data.paid_on
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise Conflict(f"Reference {data.reference} is already in use") from exc
    session.refresh(loan)
    return loan, True
