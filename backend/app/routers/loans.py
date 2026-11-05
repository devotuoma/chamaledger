from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import LoanCreate, LoanOut, RepaymentCreate
from app.services import loans as service

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
def issue_loan(data: LoanCreate, session: Session = Depends(get_session)):
    return service.to_out(service.issue_loan(session, data), date.today())


@router.get("", response_model=list[LoanOut])
def list_loans(session: Session = Depends(get_session)):
    today = date.today()
    return [service.to_out(loan, today) for loan in service.list_loans(session)]


@router.post("/{loan_id}/repayments", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
def record_repayment(
    loan_id: int,
    data: RepaymentCreate,
    response: Response,
    session: Session = Depends(get_session),
):
    loan, created = service.record_repayment(session, loan_id, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return service.to_out(loan, date.today())
