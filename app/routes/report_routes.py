from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.assessment import Assessment
from app.models.consultation import Consultation, Report
from app.models.patient import Patient
from app.models.user import User
from app.services.report_service import generate_consultation_report
from app.utils.auth_utils import require_roles

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate")
def generate_report(consultation_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("doctor", "admin"))):
    consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if current_user.role == "doctor" and consultation.doctor_id != current_user.doctor_id:
        raise HTTPException(status_code=403, detail="You can only generate reports for your consultations")

    appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first() if appointment else None
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    assessment = None
    if appointment and appointment.assessment_id:
        assessment = db.query(Assessment).filter(Assessment.id == appointment.assessment_id).first()

    file_url = generate_consultation_report(patient=patient, assessment=assessment, consultation=consultation)

    report = db.query(Report).filter(Report.consultation_id == consultation.id).first()
    if report:
        report.file_url = file_url
    else:
        report = Report(consultation_id=consultation.id, file_url=file_url)
        db.add(report)

    db.commit()
    db.refresh(report)
    return {"report_id": report.id, "file_url": report.file_url}
