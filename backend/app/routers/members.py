from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import MemberCreate, MemberOut
from app.services import members as service

router = APIRouter(prefix="/members", tags=["members"])


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(data: MemberCreate, session: Session = Depends(get_session)):
    return service.create_member(session, data)


@router.get("", response_model=list[MemberOut])
def list_members(session: Session = Depends(get_session)):
    return service.list_members(session)


@router.post("/{member_id}/deactivate", response_model=MemberOut)
def deactivate_member(member_id: int, session: Session = Depends(get_session)):
    member = service.deactivate_member(session, member_id)
    return MemberOut(
        id=member.id,
        full_name=member.full_name,
        phone=member.phone,
        active=member.active,
        savings=service.savings_of(session, member.id),
    )
