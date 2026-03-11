from calendar import monthrange
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.assessment import Assessment
from app.models.consultation import Consultation
from app.models.doctor import DoctorLeave
from app.models.patient import Patient
from app.models.user import User
from app.schemas.consultation_schema import ConsultationCreate, ConsultationOut
from app.services.appointment_service import DEFAULT_SLOTS, get_available_slots
from app.utils.auth_utils import require_roles

router = APIRouter(prefix="/consultations", tags=["Consultations"])
templates = Jinja2Templates(directory="templates")


@router.post("", response_model=ConsultationOut)
def create_consultation(
    payload: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor")),
):
    if current_user.doctor_id != payload.doctor_id:
        raise HTTPException(status_code=403, detail="You can only add your own consultations")

    appointment = db.query(Appointment).filter(Appointment.id == payload.appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.doctor_id != current_user.doctor_id:
        raise HTTPException(status_code=403, detail="Appointment does not belong to you")

    existing = db.query(Consultation).filter(Consultation.appointment_id == appointment.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Consultation already exists for this appointment")

    consultation = Consultation(**payload.model_dump())
    db.add(consultation)
    appointment.status = "completed"
    db.commit()
    db.refresh(consultation)
    return consultation


@router.post("/doctor/appointment/{appointment_id}/save", response_model=ConsultationOut)
def save_consultation_for_appointment(
    appointment_id: int,
    payload: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor")),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.doctor_id != current_user.doctor_id:
        raise HTTPException(status_code=403, detail="Appointment does not belong to you")

    consultation = db.query(Consultation).filter(Consultation.appointment_id == appointment.id).first()
    if consultation:
        consultation.notes = payload.notes
        consultation.diagnosis = payload.diagnosis
        consultation.recommendation = payload.recommendation
    else:
        consultation = Consultation(
            appointment_id=appointment.id,
            doctor_id=current_user.doctor_id,
            notes=payload.notes,
            diagnosis=payload.diagnosis,
            recommendation=payload.recommendation,
        )
        db.add(consultation)

    appointment.status = "completed"
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/doctor/dashboard", response_class=HTMLResponse)
def doctor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor")),
):
    today = date.today()
    appointments = (
        db.query(Appointment, Patient, Assessment)
        .join(Patient, Patient.id == Appointment.patient_id)
        .outerjoin(Assessment, Assessment.id == Appointment.assessment_id)
        .filter(Appointment.doctor_id == current_user.doctor_id, Appointment.appointment_date == today)
        .order_by(Appointment.time_slot.asc())
        .all()
    )
    return templates.TemplateResponse(
        "doctor_dashboard.html",
        {
            "request": request,
            "appointments": appointments,
            "today": today,
        },
    )


@router.get("/doctor/calendar", response_class=HTMLResponse)
def doctor_calendar_page(request: Request, _: User = Depends(require_roles("doctor"))):
    return templates.TemplateResponse("doctor_calendar.html", {"request": request})


@router.get("/doctor/calendar-data")
def doctor_calendar_data(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor")),
):
    _, days_in_month = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, days_in_month)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.appointment_date >= start,
            Appointment.appointment_date <= end,
        )
        .all()
    )
    leave_rows = (
        db.query(DoctorLeave)
        .filter(
            DoctorLeave.doctor_id == current_user.doctor_id,
            DoctorLeave.start_date <= end,
            DoctorLeave.end_date >= start,
        )
        .all()
    )

    by_day: dict[str, dict] = {}
    for i in range(1, days_in_month + 1):
        day = date(year, month, i)
        by_day[day.isoformat()] = {
            "date": day.isoformat(),
            "booked_slots": 0,
            "free_slots": len(DEFAULT_SLOTS),
            "status": "free",
        }

    for appt in appointments:
        key = appt.appointment_date.isoformat()
        if key not in by_day:
            continue
        if appt.status == "cancelled":
            continue
        by_day[key]["booked_slots"] += 1

    for key, entry in by_day.items():
        entry["free_slots"] = max(0, len(DEFAULT_SLOTS) - entry["booked_slots"])
        if entry["booked_slots"] > 0:
            entry["status"] = "booked"

    for leave in leave_rows:
        current = max(leave.start_date, start)
        last = min(leave.end_date, end)
        while current <= last:
            key = current.isoformat()
            if key in by_day:
                by_day[key]["status"] = "leave"
                by_day[key]["booked_slots"] = 0
                by_day[key]["free_slots"] = 0
            current = current.fromordinal(current.toordinal() + 1)

    return {"month": month, "year": year, "days": list(by_day.values())}


@router.get("/doctor/day-slots")
def doctor_day_slots(
    selected_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor")),
):
    appointments = (
        db.query(Appointment, Patient)
        .join(Patient, Patient.id == Appointment.patient_id)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.appointment_date == selected_date,
            Appointment.status != "cancelled",
        )
        .order_by(Appointment.time_slot.asc())
        .all()
    )
    booked = [
        {
            "appointment_id": appt.id,
            "time_slot": appt.time_slot,
            "patient_id": patient.id,
            "patient_name": patient.child_name,
            "status": appt.status,
        }
        for appt, patient in appointments
    ]

    free = get_available_slots(db, current_user.doctor_id, selected_date)
    return {
        "date": selected_date.isoformat(),
        "booked": booked,
        "free_slots": free,
    }


@router.get("/doctor/appointment/{appointment_id}", response_class=HTMLResponse)
def doctor_appointment_consultation_page(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor")),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.doctor_id != current_user.doctor_id:
        raise HTTPException(status_code=403, detail="Appointment does not belong to you")

    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    assessment = None
    if appointment.assessment_id:
        assessment = db.query(Assessment).filter(Assessment.id == appointment.assessment_id).first()

    consultation = db.query(Consultation).filter(Consultation.appointment_id == appointment.id).first()
    return templates.TemplateResponse(
        "doctor_consultation.html",
        {
            "request": request,
            "appointment": appointment,
            "patient": patient,
            "assessment": assessment,
            "consultation": consultation,
        },
    )


@router.get("/patient/my-consultations", response_class=HTMLResponse)
def patient_consultations_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("parent")),
):
    rows = (
        db.query(Consultation, Appointment, Assessment)
        .join(Appointment, Appointment.id == Consultation.appointment_id)
        .outerjoin(Assessment, Assessment.id == Appointment.assessment_id)
        .filter(Appointment.patient_id == current_user.patient_id)
        .order_by(Consultation.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "patient_consultations.html",
        {"request": request, "rows": rows},
    )


@router.get("/doctor/appointments", response_class=HTMLResponse)
def doctor_appointments_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_roles("doctor"))):
    appointments = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == current_user.doctor_id)
        .order_by(Appointment.appointment_date.desc())
        .all()
    )
    return templates.TemplateResponse("doctor_appointments.html", {"request": request, "appointments": appointments})


@router.get("/doctor/patient/{patient_id}", response_class=HTMLResponse)
def doctor_patient_detail(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor")),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    linked = db.query(Appointment).filter(Appointment.patient_id == patient.id, Appointment.doctor_id == current_user.doctor_id).first()
    if not linked:
        raise HTTPException(status_code=403, detail="Patient is not linked to your appointments")

    assessments = db.query(Assessment).filter(Assessment.patient_id == patient.id).order_by(Assessment.created_at.desc()).all()
    return templates.TemplateResponse(
        "doctor_patient_details.html",
        {"request": request, "patient": patient, "assessments": assessments},
    )


@router.get("/{consultation_id}", response_model=ConsultationOut)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor", "parent")),
):
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if current_user.role == "doctor" and consultation.doctor_id != current_user.doctor_id:
        raise HTTPException(status_code=403, detail="You can only view your own consultations")

    if current_user.role == "parent":
        appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()
        if not appointment or appointment.patient_id != current_user.patient_id:
            raise HTTPException(status_code=403, detail="You can only view your own consultations")

    return consultation
