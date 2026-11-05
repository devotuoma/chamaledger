from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import Conflict, NotFound
from app.models import Contribution, Member
from app.schemas import MemberCreate, MemberOut


def get_member(session: Session, member_id: int) -> Member:
    member = session.get(Member, member_id)
    if member is None:
        raise NotFound(f"Member {member_id} not found")
    return member


def savings_of(session: Session, member_id: int) -> int:
    total = session.scalar(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(
            Contribution.member_id == member_id
        )
    )
    return int(total)


def create_member(session: Session, data: MemberCreate) -> Member:
    # Checked up front because Postgres quotes the duplicate value in its error text, and we
    # do not want that text produced on a common path. The constraint still covers races.
    if session.scalar(select(Member.id).where(Member.phone == data.phone)) is not None:
        raise Conflict("A member with this phone number already exists")
    member = Member(full_name=data.full_name.strip(), phone=data.phone)
    session.add(member)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise Conflict("A member with this phone number already exists") from exc
    return member


def list_members(session: Session) -> list[MemberOut]:
    savings = (
        select(Contribution.member_id, func.sum(Contribution.amount).label("total"))
        .group_by(Contribution.member_id)
        .subquery()
    )
    rows = session.execute(
        select(Member, func.coalesce(savings.c.total, 0))
        .outerjoin(savings, savings.c.member_id == Member.id)
        .order_by(Member.full_name)
    )
    return [
        MemberOut(
            id=member.id,
            full_name=member.full_name,
            phone=member.phone,
            active=member.active,
            savings=int(total),
        )
        for member, total in rows
    ]


def deactivate_member(session: Session, member_id: int) -> Member:
    member = get_member(session, member_id)
    member.active = False
    session.commit()
    return member
