from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Appointment,
    Assessment,
    AssessmentQuestion,
    AssessmentResponse,
    Clinic,
    Consultation,
    Doctor,
    Patient,
    Report,
    User,
)
from app.services.question_catalog import get_seed_questions
from app.utils.auth_utils import hash_password


def upsert_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: str,
    clinic_id: int | None = None,
    doctor_id: int | None = None,
    patient_id: int | None = None,
) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)

    user.password_hash = hash_password(password)
    user.role = role
    user.clinic_id = clinic_id
    user.doctor_id = doctor_id
    user.patient_id = patient_id
    return user


def ensure_questions(db: Session) -> None:
    canonical = get_seed_questions()
    canonical_texts = [item["question"] for item in canonical]
    canonical_set = set(canonical_texts)

    rows = db.query(AssessmentQuestion).all()
    seen: set[str] = set()
    for row in rows:
        if row.question not in canonical_set:
            db.delete(row)
            continue
        if row.question in seen:
            db.delete(row)
            continue
        seen.add(row.question)

    db.flush()
    by_question = {row.question: row for row in db.query(AssessmentQuestion).all()}
    for item in canonical:
        existing = by_question.get(item["question"])
        if existing:
            existing.option_a = item["option_a"]
            existing.option_b = item["option_b"]
            existing.option_c = item["option_c"]
            existing.option_d = item["option_d"]
            existing.score_a = item["score_a"]
            existing.score_b = item["score_b"]
            existing.score_c = item["score_c"]
            existing.score_d = item["score_d"]
        else:
            db.add(AssessmentQuestion(**item))


def upsert_clinic(db: Session, name: str, address: str, phone: str) -> Clinic:
    clinic = db.query(Clinic).filter(Clinic.name == name).first()
    if not clinic:
        clinic = Clinic(name=name, address=address, phone=phone)
        db.add(clinic)
    else:
        clinic.address = address
        clinic.phone = phone
    return clinic


def upsert_doctor(
    db: Session,
    clinic_id: int,
    *,
    name: str,
    specialization: str,
    email: str,
    phone: str,
) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.email == email).first()
    if not doctor:
        doctor = Doctor(
            clinic_id=clinic_id,
            name=name,
            specialization=specialization,
            email=email,
            phone=phone,
        )
        db.add(doctor)
    else:
        doctor.clinic_id = clinic_id
        doctor.name = name
        doctor.specialization = specialization
        doctor.phone = phone
    return doctor


def upsert_patient(
    db: Session,
    clinic_id: int,
    *,
    parent_name: str,
    child_name: str,
    child_age: int,
    email: str,
    phone: str,
) -> Patient:
    patient = db.query(Patient).filter(Patient.email == email).first()
    if not patient:
        patient = Patient(
            clinic_id=clinic_id,
            parent_name=parent_name,
            child_name=child_name,
            child_age=child_age,
            email=email,
            phone=phone,
        )
        db.add(patient)
    else:
        patient.clinic_id = clinic_id
        patient.parent_name = parent_name
        patient.child_name = child_name
        patient.child_age = child_age
        patient.phone = phone
    return patient


def upsert_assessment(db: Session, patient_id: int, clinic_id: int, score: int, risk_level: str) -> Assessment:
    assessment = (
        db.query(Assessment)
        .filter(
            Assessment.patient_id == patient_id,
            Assessment.clinic_id == clinic_id,
            Assessment.score == score,
            Assessment.risk_level == risk_level,
        )
        .first()
    )
    if not assessment:
        assessment = Assessment(patient_id=patient_id, clinic_id=clinic_id, score=score, risk_level=risk_level)
        db.add(assessment)
    return assessment


def normalize_patient_assessments(
    db: Session,
    *,
    patient_id: int,
    clinic_id: int,
    score: int,
    risk_level: str,
) -> Assessment:
    canonical = upsert_assessment(db, patient_id, clinic_id, score, risk_level)
    db.flush()

    db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.assessment_id.isnot(None),
    ).update({Appointment.assessment_id: canonical.id})

    extras = (
        db.query(Assessment)
        .filter(Assessment.patient_id == patient_id, Assessment.id != canonical.id)
        .all()
    )
    for item in extras:
        db.delete(item)
    return canonical


def ensure_assessment_answers(db: Session, assessment: Assessment, risk_level: str) -> None:
    existing = db.query(AssessmentResponse).filter(AssessmentResponse.assessment_id == assessment.id).count()
    if existing > 0:
        return

    questions = db.query(AssessmentQuestion).order_by(AssessmentQuestion.id.asc()).all()
    risk_option = {
        "Low Risk": ("b", 1),
        "Moderate Risk": ("c", 2),
        "High Risk": ("d", 3),
    }.get(risk_level, ("b", 1))
    option_key = risk_option[0]

    for q in questions:
        db.add(
            AssessmentResponse(
                assessment_id=assessment.id,
                question_id=q.id,
                selected_option=option_key,
                selected_text=getattr(q, f"option_{option_key}"),
                score=getattr(q, f"score_{option_key}"),
            )
        )


def upsert_appointment(
    db: Session,
    *,
    clinic_id: int,
    doctor_id: int,
    patient_id: int,
    assessment_id: int | None,
    appointment_date: date,
    time_slot: str,
    status: str,
) -> Appointment:
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.patient_id == patient_id,
            Appointment.appointment_date == appointment_date,
            Appointment.time_slot == time_slot,
        )
        .first()
    )
    if not appointment:
        appointment = Appointment(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            assessment_id=assessment_id,
            appointment_date=appointment_date,
            time_slot=time_slot,
            status=status,
        )
        db.add(appointment)
    else:
        appointment.clinic_id = clinic_id
        appointment.assessment_id = assessment_id
        appointment.status = status
    return appointment


def upsert_consultation(
    db: Session,
    *,
    appointment_id: int,
    doctor_id: int,
    notes: str,
    diagnosis: str,
    recommendation: str,
) -> Consultation:
    consultation = db.query(Consultation).filter(Consultation.appointment_id == appointment_id).first()
    if not consultation:
        consultation = Consultation(
            appointment_id=appointment_id,
            doctor_id=doctor_id,
            notes=notes,
            diagnosis=diagnosis,
            recommendation=recommendation,
        )
        db.add(consultation)
    else:
        consultation.doctor_id = doctor_id
        consultation.notes = notes
        consultation.diagnosis = diagnosis
        consultation.recommendation = recommendation
    return consultation


def upsert_report(db: Session, consultation_id: int, file_url: str) -> Report:
    report = db.query(Report).filter(Report.consultation_id == consultation_id).first()
    if not report:
        report = Report(consultation_id=consultation_id, file_url=file_url)
        db.add(report)
    else:
        report.file_url = file_url
    return report


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        ensure_questions(db)

        clinic = upsert_clinic(db, "Hope Neuro Clinic", "MG Road, Bengaluru", "+91-9000000000")
        db.flush()

        admin = upsert_user(
            db,
            email="admin@clinic.com",
            password="Admin@123",
            role="admin",
            clinic_id=clinic.id,
        )

        doctor_1 = upsert_doctor(
            db,
            clinic.id,
            name="Dr. Meera Iyer",
            specialization="Developmental Pediatrician",
            email="meera.iyer@clinic.com",
            phone="+91-9000000011",
        )
        doctor_2 = upsert_doctor(
            db,
            clinic.id,
            name="Dr. Arjun Rao",
            specialization="Child Psychiatrist",
            email="arjun.rao@clinic.com",
            phone="+91-9000000012",
        )
        db.flush()

        upsert_user(
            db,
            email=doctor_1.email,
            password="Doctor@123",
            role="doctor",
            clinic_id=clinic.id,
            doctor_id=doctor_1.id,
        )
        upsert_user(
            db,
            email=doctor_2.email,
            password="Doctor@123",
            role="doctor",
            clinic_id=clinic.id,
            doctor_id=doctor_2.id,
        )

        patient_1 = upsert_patient(
            db,
            clinic.id,
            parent_name="Anita Sharma",
            child_name="Riaan Sharma",
            child_age=4,
            email="anita.parent1@clinic.com",
            phone="+91-9000000101",
        )
        patient_2 = upsert_patient(
            db,
            clinic.id,
            parent_name="Rahul Verma",
            child_name="Aarav Verma",
            child_age=6,
            email="rahul.parent2@clinic.com",
            phone="+91-9000000102",
        )
        patient_3 = upsert_patient(
            db,
            clinic.id,
            parent_name="Sneha Nair",
            child_name="Mia Nair",
            child_age=3,
            email="sneha.parent3@clinic.com",
            phone="+91-9000000103",
        )
        db.flush()

        upsert_user(
            db,
            email=patient_1.email,
            password="Parent@123",
            role="parent",
            clinic_id=clinic.id,
            patient_id=patient_1.id,
        )
        upsert_user(
            db,
            email=patient_2.email,
            password="Parent@123",
            role="parent",
            clinic_id=clinic.id,
            patient_id=patient_2.id,
        )
        upsert_user(
            db,
            email=patient_3.email,
            password="Parent@123",
            role="parent",
            clinic_id=clinic.id,
            patient_id=patient_3.id,
        )

        assessment_low = normalize_patient_assessments(
            db,
            patient_id=patient_1.id,
            clinic_id=clinic.id,
            score=20,
            risk_level="Low Risk",
        )
        assessment_mid = normalize_patient_assessments(
            db,
            patient_id=patient_2.id,
            clinic_id=clinic.id,
            score=55,
            risk_level="Moderate Risk",
        )
        assessment_high = normalize_patient_assessments(
            db,
            patient_id=patient_3.id,
            clinic_id=clinic.id,
            score=95,
            risk_level="High Risk",
        )
        ensure_assessment_answers(db, assessment_low, "Low Risk")
        ensure_assessment_answers(db, assessment_mid, "Moderate Risk")
        ensure_assessment_answers(db, assessment_high, "High Risk")
        db.flush()

        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        appt_1 = upsert_appointment(
            db,
            clinic_id=clinic.id,
            doctor_id=doctor_1.id,
            patient_id=patient_1.id,
            assessment_id=assessment_low.id,
            appointment_date=today,
            time_slot="09:00-09:30",
            status="scheduled",
        )
        appt_2 = upsert_appointment(
            db,
            clinic_id=clinic.id,
            doctor_id=doctor_1.id,
            patient_id=patient_2.id,
            assessment_id=assessment_mid.id,
            appointment_date=today,
            time_slot="09:30-10:00",
            status="scheduled",
        )
        appt_3 = upsert_appointment(
            db,
            clinic_id=clinic.id,
            doctor_id=doctor_2.id,
            patient_id=patient_3.id,
            assessment_id=assessment_high.id,
            appointment_date=tomorrow,
            time_slot="10:00-10:30",
            status="scheduled",
        )
        appt_4 = upsert_appointment(
            db,
            clinic_id=clinic.id,
            doctor_id=doctor_2.id,
            patient_id=patient_2.id,
            assessment_id=assessment_mid.id,
            appointment_date=yesterday,
            time_slot="11:00-11:30",
            status="completed",
        )
        appt_5 = upsert_appointment(
            db,
            clinic_id=clinic.id,
            doctor_id=doctor_1.id,
            patient_id=patient_3.id,
            assessment_id=assessment_high.id,
            appointment_date=tomorrow,
            time_slot="11:30-12:00",
            status="cancelled",
        )
        db.flush()

        consultation = upsert_consultation(
            db,
            appointment_id=appt_4.id,
            doctor_id=doctor_2.id,
            notes="Child shows repetitive play and delayed social reciprocity.",
            diagnosis="Autism Spectrum Disorder - needs multidisciplinary evaluation",
            recommendation="Begin speech therapy and occupational therapy; follow-up in 2 weeks.",
        )
        db.flush()

        upsert_report(
            db,
            consultation_id=consultation.id,
            file_url="https://example.com/reports/sample-consultation-report.pdf",
        )

        db.commit()

        print("Seed complete.")
        print("\nTest Credentials")
        print("Admin  : admin@clinic.com / Admin@123")
        print("Doctor : meera.iyer@clinic.com / Doctor@123")
        print("Doctor : arjun.rao@clinic.com / Doctor@123")
        print("Parent : anita.parent1@clinic.com / Parent@123")
        print("Parent : rahul.parent2@clinic.com / Parent@123")
        print("Parent : sneha.parent3@clinic.com / Parent@123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
