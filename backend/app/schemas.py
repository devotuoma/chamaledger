from datetime import date

from pydantic import BaseModel, ConfigDict, Field

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
