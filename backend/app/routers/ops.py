import hmac
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import faults
from app.config import get_settings
from app.db import engine, get_session
from app.schemas import ContributionCreate, MemberCreate
from app.services.contributions import record_contribution
from app.services.members import create_member

PROBE_PHONE = "+19999999999"


def require_ops_token(x_ops_token: str = Header(default="")) -> None:
    expected = get_settings().ops_token
    if not expected:
        raise HTTPException(status_code=404, detail="Not found")
    if not hmac.compare_digest(x_ops_token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid ops token")


router = APIRouter(prefix="/ops", tags=["ops"], dependencies=[Depends(require_ops_token)])


class FlagUpdate(BaseModel):
    enabled: bool


@router.get("/flags")
def list_flags(session: Session = Depends(get_session)) -> dict[str, bool]:
    return faults.list_flags(session)


@router.put("/flags/{name}")
def set_flag(
    name: str, update: FlagUpdate, session: Session = Depends(get_session)
) -> dict[str, bool]:
    faults.set_flag(session, name, update.enabled)
    return faults.list_flags(session)


@router.post("/probe")
def probe() -> dict[str, str]:
    """Runs the real journey against the real database, then rolls everything back."""
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                member = create_member(
                    session, MemberCreate(full_name="Synthetic Probe", phone=PROBE_PHONE)
                )
                record_contribution(
                    session,
                    ContributionCreate(
                        member_id=member.id,
                        amount=1,
                        paid_on=date.today(),
                        reference="SYNTHETIC-PROBE",
                    ),
                )
        finally:
            transaction.rollback()
    return {"status": "ok"}
