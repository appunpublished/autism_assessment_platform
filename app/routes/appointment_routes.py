from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.assessment import Assessment
from app.models.patient import Patient
from app.models.user import User
from app.schemas.appointment_schema import AppointmentBook, AppointmentOut, AppointmentReschedule
from app.services.appointment_service import ensure_slot_available, get_available_slots, is_doctor_on_leave
from app.utils.auth_utils import get_current_user, require_roles

router = APIRouter(prefix="/appointments", tags=["Appointments"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_model=list[AppointmentOut])
def list_appointments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Appointment)
    if current_user.role == "doctor":
        query = query.filter(Appointment.doctor_id == current_user.doctor_id)
    elif current_user.role == "parent":
        query = query.filter(Appointment.patient_id == current_user.patient_id)
    return query.order_by(Appointment.appointment_date.asc()).all()


@router.get("/slots")
def available_slots(
    doctor_id: int = Query(...),
    appointment_date: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    on_leave = is_doctor_on_leave(db, doctor_id, appointment_date)
    return {
        "doctor_id": doctor_id,
        "appointment_date": appointment_date,
        "on_leave": on_leave,
        "slots": get_available_slots(db, doctor_id, appointment_date),
    }


@router.post("/book", response_model=AppointmentOut)
def book_appointment(
    payload: AppointmentBook,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "parent")),
):
    if current_user.role == "parent" and current_user.patient_id != payload.patient_id:
        raise HTTPException(status_code=403, detail="You can only book for your child")

    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if payload.assessment_id is None:
        raise HTTPException(status_code=400, detail="Assessment is required for risk-based appointment booking")

    assessment = db.query(Assessment).filter(Assessment.id == payload.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.patient_id != payload.patient_id:
        raise HTTPException(status_code=400, detail="Assessment does not belong to selected patient")

    ensure_slot_available(db, payload.doctor_id, payload.appointment_date, payload.time_slot)
    appointment = Appointment(**payload.model_dump(), status="scheduled")
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.put("/reschedule", response_model=AppointmentOut)
def reschedule_appointment(
    payload: AppointmentReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "parent")),
):
    appointment = db.query(Appointment).filter(Appointment.id == payload.appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role == "parent" and current_user.patient_id != appointment.patient_id:
        raise HTTPException(status_code=403, detail="You can only reschedule your own appointment")

    ensure_slot_available(db, appointment.doctor_id, payload.appointment_date, payload.time_slot)
    appointment.appointment_date = payload.appointment_date
    appointment.time_slot = payload.time_slot
    appointment.status = "scheduled"
    db.commit()
    db.refresh(appointment)
    return appointment


@router.delete("/cancel")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "parent")),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role == "parent" and current_user.patient_id != appointment.patient_id:
        raise HTTPException(status_code=403, detail="You can only cancel your own appointment")

    appointment.status = "cancelled"
    db.commit()
    return {"message": "Appointment cancelled"}


@router.get("/booking-page", response_class=HTMLResponse)
def booking_page(request: Request):
    return templates.TemplateResponse("appointment_booking.html", {"request": request})
