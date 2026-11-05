from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import ContributionCreate, ContributionOut
from app.services import contributions as service

router = APIRouter(prefix="/contributions", tags=["contributions"])


@router.post("", response_model=ContributionOut, status_code=status.HTTP_201_CREATED)
def record_contribution(
    data: ContributionCreate, response: Response, session: Session = Depends(get_session)
):
    contribution, created = service.record_contribution(session, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return contribution


@router.get("", response_model=list[ContributionOut])
def list_contributions(
    member_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    return service.list_contributions(session, member_id, limit)
