from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

E164 = r"^\+[1-9]\d{7,14}$"


class MemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(pattern=E164)


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str
    active: bool
    savings: int = 0


class ContributionCreate(BaseModel):
    member_id: int
    amount: int = Field(gt=0)
    paid_on: date
    reference: str = Field(min_length=3, max_length=64)
    note: str | None = Field(default=None, max_length=200)


class ContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    amount: int
    paid_on: date
    reference: str
    note: str | None


class LoanCreate(BaseModel):
    member_id: int
    principal: int = Field(gt=0)
    interest_rate_bps: int = Field(default=1000, ge=0, le=10_000)
    issued_on: date
    due_on: date

    @model_validator(mode="after")
    def due_after_issue(self) -> "LoanCreate":
        if self.due_on <= self.issued_on:
            raise ValueError("due_on must be after issued_on")
        return self


class LoanOut(BaseModel):
    id: int
    member_id: int
    principal: int
    interest_rate_bps: int
    issued_on: date
    due_on: date
    closed_on: date | None
    total_due: int
    outstanding: int
    days_late: int


class RepaymentCreate(BaseModel):
    amount: int = Field(gt=0)
    paid_on: date
    reference: str = Field(min_length=3, max_length=64)
