from datetime import date

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.doctor import DoctorLeave


DEFAULT_SLOTS = [
    "09:00-09:30",
    "09:30-10:00",
    "10:00-10:30",
    "10:30-11:00",
    "11:00-11:30",
    "11:30-12:00",
    "14:00-14:30",
    "14:30-15:00",
    "15:00-15:30",
    "15:30-16:00",
]


class SlotAvailabilityError(Exception):
    def __init__(self, detail: str, status_code: int = 409):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def is_doctor_on_leave(db: Session, doctor_id: int, appointment_date: date) -> bool:
    leave = (
        db.query(DoctorLeave)
        .filter(
            DoctorLeave.doctor_id == doctor_id,
            DoctorLeave.start_date <= appointment_date,
            DoctorLeave.end_date >= appointment_date,
        )
        .first()
    )
    return bool(leave)


def get_available_slots(db: Session, doctor_id: int, appointment_date: date) -> list[str]:
    if is_doctor_on_leave(db, doctor_id, appointment_date):
        return []

    booked = (
        db.query(Appointment.time_slot)
        .filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date,
                Appointment.status == "scheduled",
            )
        )
        .all()
    )
    booked_set = {slot for (slot,) in booked}
    return [slot for slot in DEFAULT_SLOTS if slot not in booked_set]


def ensure_slot_available(db: Session, doctor_id: int, appointment_date: date, time_slot: str) -> None:
    if is_doctor_on_leave(db, doctor_id, appointment_date):
        raise SlotAvailabilityError("Doctor is out of office on selected date")

    conflict = (
        db.query(Appointment)
        .filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date,
                Appointment.time_slot == time_slot,
                Appointment.status == "scheduled",
            )
        )
        .first()
    )
    if conflict:
        raise SlotAvailabilityError("Time slot is already booked")
