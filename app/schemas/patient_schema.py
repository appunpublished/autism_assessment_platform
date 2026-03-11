from datetime import datetime

from pydantic import BaseModel, Field


class PatientBase(BaseModel):
    clinic_id: int
    parent_name: str
    child_name: str
    child_age: int = Field(ge=1, le=18)
    email: str
    phone: str


class PatientCreate(PatientBase):
    password: str | None = None


class PatientOut(PatientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
