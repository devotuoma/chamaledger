"""Fills an empty database with invented demo data so reviewers see a working group."""

from datetime import date, timedelta

from sqlalchemy import func, select

from app.db import SessionLocal
from app.domain import total_due
from app.models import Contribution, Loan, Member, Repayment

MEMBERS = [
    ("Demo Akinyi", "+256700100001", 240_000),
    ("Demo Mugisha", "+256700100002", 180_000),
    ("Demo Nakato", "+256700100003", 320_000),
    ("Demo Otieno", "+256700100004", 90_000),
]


def seed(today: date | None = None) -> bool:
    """Returns True if data was inserted. Does nothing if any member already exists."""
    today = today or date.today()
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(Member)):
            return False

        members = []
        for index, (name, phone, saved) in enumerate(MEMBERS):
            member = Member(full_name=name, phone=phone)
            session.add(member)
            session.flush()
            session.add(
                Contribution(
                    member_id=member.id,
                    amount=saved,
                    paid_on=today - timedelta(days=90),
                    reference=f"DEMO-SAVE-{index}",
                )
            )
            members.append(member)

        late = Loan(
            member_id=members[3].id,
            principal=150_000,
            interest_rate_bps=1000,
            issued_on=today - timedelta(days=120),
            due_on=today - timedelta(days=45),
        )
        current = Loan(
            member_id=members[0].id,
            principal=300_000,
            interest_rate_bps=1000,
            issued_on=today - timedelta(days=20),
            due_on=today + timedelta(days=70),
        )
        session.add_all([late, current])
        session.flush()
        session.add(
            Repayment(
                loan_id=current.id,
                amount=total_due(current.principal, current.interest_rate_bps) // 4,
                paid_on=today - timedelta(days=5),
                reference="DEMO-REPAY-0",
            )
        )
        session.commit()
    return True


if __name__ == "__main__":
    print("Demo data inserted" if seed() else "Database already has data; seed skipped")
