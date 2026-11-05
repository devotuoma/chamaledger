from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import Conflict
from app.faults import apply_contribution_faults
from app.models import Contribution
from app.schemas import ContributionCreate
from app.services.members import get_member
from app.telemetry import journey_span


def _find_by_reference(session: Session, reference: str) -> Contribution | None:
    return session.scalar(select(Contribution).where(Contribution.reference == reference))


def _replay(existing: Contribution, data: ContributionCreate) -> Contribution:
    same = (
        existing.member_id == data.member_id
        and existing.amount == data.amount
        and existing.paid_on == data.paid_on
    )
    if not same:
        raise Conflict(f"Reference {data.reference} was already used for a different payment")
    return existing


def record_contribution(session: Session, data: ContributionCreate) -> tuple[Contribution, bool]:
    """Returns the contribution and whether this call created it."""
    with journey_span("record_contribution") as span:
        contribution, created = _record(session, data)
        span.set_attribute("chama.contribution.created", created)
        return contribution, created


def _record(session: Session, data: ContributionCreate) -> tuple[Contribution, bool]:
    apply_contribution_faults(session)
    existing = _find_by_reference(session, data.reference)
    if existing is not None:
        return _replay(existing, data), False

    member = get_member(session, data.member_id)
    if not member.active:
        raise Conflict("This member is inactive and cannot make contributions")

    contribution = Contribution(
        member_id=data.member_id,
        amount=data.amount,
        paid_on=data.paid_on,
        reference=data.reference,
        note=data.note,
    )
    session.add(contribution)
    try:
        session.commit()
    except IntegrityError:
        # A concurrent retry won the race on the unique reference.
        session.rollback()
        return _replay(_find_by_reference(session, data.reference), data), False
    return contribution, True


def list_contributions(
    session: Session, member_id: int | None = None, limit: int = 100
) -> list[Contribution]:
    query = select(Contribution).order_by(Contribution.id.desc()).limit(limit)
    if member_id is not None:
        query = query.where(Contribution.member_id == member_id)
    return list(session.scalars(query))
