from datetime import datetime

from pydantic import BaseModel


class ClinicBase(BaseModel):
    name: str
    address: str
    phone: str


class ClinicCreate(ClinicBase):
    pass


class ClinicOut(ClinicBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
