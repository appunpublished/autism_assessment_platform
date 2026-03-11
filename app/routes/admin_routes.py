from datetime import date

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.assessment import Assessment
from app.models.doctor import Doctor, DoctorLeave
from app.models.patient import Patient
from app.models.user import User
from app.utils.auth_utils import require_roles

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


class DoctorLeaveCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = ""
    status: str = "out_of_office"


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    today = date.today()
    total_assessments = db.query(func.count(Assessment.id)).scalar() or 0
    high_risk_cases = db.query(func.count(Assessment.id)).filter(Assessment.risk_level == "High Risk").scalar() or 0
    appointments_today = (
        db.query(func.count(Appointment.id)).filter(Appointment.appointment_date == today, Appointment.status == "scheduled").scalar() or 0
    )

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "total_assessments": total_assessments,
            "high_risk_cases": high_risk_cases,
            "appointments_today": appointments_today,
        },
    )


@router.get("/doctors", response_class=HTMLResponse)
def manage_doctors(request: Request, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    doctors = db.query(Doctor).order_by(Doctor.created_at.desc()).all()
    return templates.TemplateResponse("manage_doctors.html", {"request": request, "doctors": doctors})


@router.get("/patients", response_class=HTMLResponse)
def manage_patients(request: Request, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    return templates.TemplateResponse("manage_patients.html", {"request": request, "patients": patients})


@router.get("/appointments", response_class=HTMLResponse)
def manage_appointments(request: Request, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    appointments = db.query(Appointment).order_by(Appointment.appointment_date.desc()).all()
    return templates.TemplateResponse("manage_appointments.html", {"request": request, "appointments": appointments})


@router.post("/doctors/{doctor_id}/leave")
def mark_doctor_leave(
    doctor_id: int,
    payload: DoctorLeaveCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="Invalid date range")

    leave = DoctorLeave(
        doctor_id=doctor_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=payload.status or "out_of_office",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return {"message": "Doctor leave marked", "leave_id": leave.id}
