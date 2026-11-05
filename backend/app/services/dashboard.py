from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import OpenLoan, portfolio_at_risk
from app.models import Contribution, Member
from app.schemas import DashboardOut
from app.services.loans import open_loans, outstanding_of


def build_dashboard(session: Session, as_of: date) -> DashboardOut:
    loans = [
        OpenLoan(due_on=loan.due_on, outstanding=outstanding_of(loan))
        for loan in open_loans(session)
    ]
    members = session.scalar(select(func.count()).select_from(Member).where(Member.active))
    savings = session.scalar(select(func.coalesce(func.sum(Contribution.amount), 0)))
    return DashboardOut(
        member_count=members,
        total_savings=int(savings),
        loans_outstanding=sum(loan.outstanding for loan in loans),
        par30=round(portfolio_at_risk(loans, as_of), 4),
        as_of=as_of,
    )
