from datetime import date

from pydantic import BaseModel, Field


class AppointmentBook(BaseModel):
    clinic_id: int
    doctor_id: int
    patient_id: int
    assessment_id: int
    appointment_date: date
    time_slot: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d-[0-2]\d:[0-5]\d$")


class AppointmentReschedule(BaseModel):
    appointment_id: int
    appointment_date: date
    time_slot: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d-[0-2]\d:[0-5]\d$")


class AppointmentOut(BaseModel):
    id: int
    clinic_id: int
    doctor_id: int
    patient_id: int
    assessment_id: int | None
    appointment_date: date
    time_slot: str
    status: str

    class Config:
        from_attributes = True
