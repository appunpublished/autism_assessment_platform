from datetime import datetime

from pydantic import BaseModel


class ConsultationCreate(BaseModel):
    appointment_id: int
    doctor_id: int
    notes: str
    diagnosis: str
    recommendation: str


class ConsultationOut(BaseModel):
    id: int
    appointment_id: int
    doctor_id: int
    notes: str
    diagnosis: str
    recommendation: str
    created_at: datetime

    class Config:
        from_attributes = True
