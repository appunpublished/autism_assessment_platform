from datetime import datetime

from pydantic import BaseModel


class DoctorBase(BaseModel):
    clinic_id: int
    name: str
    specialization: str
    email: str
    phone: str


class DoctorCreate(DoctorBase):
    password: str | None = None


class DoctorOut(DoctorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
