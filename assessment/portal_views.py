import json
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func

from app.config import settings as app_settings
from app.database import Base, SessionLocal, engine
from app.models.appointment import Appointment
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentResponse
from app.models.clinic import Clinic
from app.models.consultation import Consultation, Report
from app.models.doctor import Doctor, DoctorLeave
from app.models.patient import Patient
from app.models.user import User
from app.services.appointment_service import (
    DEFAULT_SLOTS,
    SlotAvailabilityError,
    ensure_slot_available,
    get_available_slots,
)
from app.services.question_catalog import get_seed_questions
from app.services.question_catalog import get_question_section
from app.services.report_service import generate_consultation_report


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _extract_token(raw_token: str | None) -> str | None:
    if not raw_token:
        return None
    if raw_token.lower().startswith("bearer "):
        return raw_token.split(" ", 1)[1].strip()
    return raw_token.strip()


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


def _parse_json(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def _serialize_clinic(clinic: Clinic) -> dict:
    return {"id": clinic.id, "name": clinic.name, "address": clinic.address, "phone": clinic.phone}


def _serialize_doctor(doctor: Doctor) -> dict:
    return {
        "id": doctor.id,
        "clinic_id": doctor.clinic_id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "email": doctor.email,
        "phone": doctor.phone,
        "created_at": doctor.created_at.isoformat(),
    }


def _serialize_patient(patient: Patient) -> dict:
    return {
        "id": patient.id,
        "clinic_id": patient.clinic_id,
        "parent_name": patient.parent_name,
        "child_name": patient.child_name,
        "child_age": patient.child_age,
        "email": patient.email,
        "phone": patient.phone,
        "created_at": patient.created_at.isoformat(),
    }


def _serialize_assessment(assessment: Assessment) -> dict:
    return {
        "id": assessment.id,
        "patient_id": assessment.patient_id,
        "clinic_id": assessment.clinic_id,
        "score": assessment.score,
        "risk_level": assessment.risk_level,
        "created_at": assessment.created_at.isoformat(),
    }


def _serialize_consultation(consultation: Consultation) -> dict:
    return {
        "id": consultation.id,
        "appointment_id": consultation.appointment_id,
        "doctor_id": consultation.doctor_id,
        "notes": consultation.notes,
        "diagnosis": consultation.diagnosis,
        "recommendation": consultation.recommendation,
        "created_at": consultation.created_at.isoformat(),
    }


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def _create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=app_settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, app_settings.secret_key, algorithm=app_settings.algorithm)


def _get_current_user(request: HttpRequest, db, required_roles: tuple[str, ...] | None = None):
    raw_token = request.META.get("HTTP_AUTHORIZATION") or request.COOKIES.get("access_token")
    bearer_token = _extract_token(raw_token)
    if not bearer_token:
        return None

    try:
        payload = jwt.decode(bearer_token, app_settings.secret_key, algorithms=[app_settings.algorithm])
        email = payload.get("sub")
    except JWTError:
        return None

    if not email:
        return None

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if required_roles and user.role not in required_roles:
        return False
    return user


def _require_page_user(request: HttpRequest, roles: tuple[str, ...]):
    db = SessionLocal()
    try:
        user = _get_current_user(request, db, roles)
        if not user:
            return None, redirect("/login")
        if user is False:
            return None, redirect("/")
        return user, None
    finally:
        db.close()


def _require_api_user(request: HttpRequest, db, roles: tuple[str, ...]):
    user = _get_current_user(request, db, roles)
    if not user:
        return None, _json_error("Invalid credentials", 401)
    if user is False:
        return None, _json_error("Insufficient permissions", 403)
    return user, None


def _initialize_portal_data() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).first()
        if not clinic:
            clinic = Clinic(name="Hope Neuro Clinic", address="MG Road", phone="+91-9000000000")
            db.add(clinic)
            db.flush()

        admin_user = db.query(User).filter(User.email == app_settings.default_admin_email).first()
        if not admin_user:
            db.add(
                User(
                    email=app_settings.default_admin_email,
                    password_hash=_hash_password(app_settings.default_admin_password),
                    role="admin",
                    clinic_id=clinic.id,
                )
            )

        existing_questions = {question for (question,) in db.query(AssessmentQuestion.question).all()}
        for item in get_seed_questions():
            if item["question"] not in existing_questions:
                db.add(AssessmentQuestion(**item))

        db.commit()
    finally:
        db.close()


_initialize_portal_data()


@require_GET
def login_page(request: HttpRequest) -> HttpResponse:
    return render(request, "login.html")


@csrf_exempt
@require_http_methods(["POST"])
def auth_login(request: HttpRequest) -> JsonResponse:
    payload = _parse_json(request)
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not _verify_password(password, user.password_hash):
            return _json_error("Invalid email or password", 401)

        token = _create_access_token(subject=user.email, role=user.role)
        response = JsonResponse({"access_token": token, "role": user.role})
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            samesite="Lax",
            secure=False,
            max_age=60 * 60,
            path="/",
        )
        return response
    finally:
        db.close()


@csrf_exempt
@require_http_methods(["POST"])
def auth_logout(request: HttpRequest) -> JsonResponse:
    response = JsonResponse({"message": "Logged out successfully"})
    response.delete_cookie(key="access_token", path="/")
    return response


@require_GET
def clinics_api(request: HttpRequest) -> JsonResponse:
    db = SessionLocal()
    try:
        clinics = db.query(Clinic).order_by(Clinic.name.asc()).all()
        return JsonResponse([_serialize_clinic(clinic) for clinic in clinics], safe=False)
    finally:
        db.close()


@require_http_methods(["GET", "POST"])
@csrf_exempt
def doctors_api(request: HttpRequest, doctor_id: int | None = None) -> JsonResponse:
    db = SessionLocal()
    try:
        if request.method == "GET":
            if doctor_id is not None:
                doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
                if not doctor:
                    return _json_error("Doctor not found", 404)
                return JsonResponse(_serialize_doctor(doctor))
            doctors = db.query(Doctor).order_by(Doctor.created_at.desc()).all()
            return JsonResponse([_serialize_doctor(doctor) for doctor in doctors], safe=False)

        user, error = _require_api_user(request, db, ("admin",))
        if error:
            return error

        payload = _parse_json(request)
        if db.query(Doctor).filter(Doctor.email == payload.get("email")).first():
            return _json_error("Doctor email already exists", 409)

        doctor = Doctor(
            clinic_id=int(payload.get("clinic_id")),
            name=(payload.get("name") or "").strip(),
            specialization=(payload.get("specialization") or "").strip(),
            email=(payload.get("email") or "").strip(),
            phone=(payload.get("phone") or "").strip(),
        )
        db.add(doctor)
        db.flush()

        if payload.get("password"):
            db.add(
                User(
                    email=doctor.email,
                    password_hash=_hash_password(payload["password"]),
                    role="doctor",
                    clinic_id=doctor.clinic_id,
                    doctor_id=doctor.id,
                )
            )

        db.commit()
        db.refresh(doctor)
        return JsonResponse(_serialize_doctor(doctor), status=201)
    finally:
        db.close()


@require_http_methods(["GET", "POST"])
@csrf_exempt
def patients_api(request: HttpRequest, patient_id: int | None = None) -> JsonResponse:
    db = SessionLocal()
    try:
        if request.method == "GET":
            user, error = _require_api_user(request, db, ("admin", "doctor", "parent"))
            if error:
                return error

            if patient_id is not None:
                patient = db.query(Patient).filter(Patient.id == patient_id).first()
                if not patient:
                    return _json_error("Patient not found", 404)
                if user.role == "parent" and user.patient_id != patient.id:
                    return _json_error("You can only view your child data", 403)
                return JsonResponse(_serialize_patient(patient))

            query = db.query(Patient)
            if user.role == "parent":
                query = query.filter(Patient.id == user.patient_id)
            patients = query.order_by(Patient.created_at.desc()).all()
            return JsonResponse([_serialize_patient(patient) for patient in patients], safe=False)

        user, error = _require_api_user(request, db, ("admin",))
        if error:
            return error

        payload = _parse_json(request)
        if db.query(Patient).filter(Patient.email == payload.get("email")).first():
            return _json_error("Patient email already exists", 409)

        patient = Patient(
            clinic_id=int(payload.get("clinic_id")),
            parent_name=(payload.get("parent_name") or "").strip(),
            child_name=(payload.get("child_name") or "").strip(),
            child_age=int(payload.get("child_age")),
            email=(payload.get("email") or "").strip(),
            phone=(payload.get("phone") or "").strip(),
        )
        db.add(patient)
        db.flush()

        if payload.get("password"):
            db.add(
                User(
                    email=patient.email,
                    password_hash=_hash_password(payload["password"]),
                    role="parent",
                    clinic_id=patient.clinic_id,
                    patient_id=patient.id,
                )
            )

        db.commit()
        db.refresh(patient)
        return JsonResponse(_serialize_patient(patient), status=201)
    finally:
        db.close()


@require_GET
def assessment_patient_api(request: HttpRequest, patient_id: int) -> JsonResponse:
    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("admin", "doctor", "parent"))
        if error:
            return error
        if user.role == "parent" and user.patient_id != patient_id:
            return _json_error("You can only view your own child assessments", 403)

        assessments = (
            db.query(Assessment)
            .filter(Assessment.patient_id == patient_id)
            .order_by(Assessment.created_at.desc())
            .all()
        )
        return JsonResponse([_serialize_assessment(item) for item in assessments], safe=False)
    finally:
        db.close()


@require_GET
def assessment_details_api(request: HttpRequest, assessment_id: int) -> JsonResponse:
    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("admin", "doctor", "parent"))
        if error:
            return error

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            return _json_error("Assessment not found", 404)

        patient = db.query(Patient).filter(Patient.id == assessment.patient_id).first()
        if user.role == "parent" and user.patient_id != assessment.patient_id:
            return _json_error("You can only view your own child assessments", 403)
        if user.role == "doctor":
            linked = (
                db.query(Appointment)
                .filter(
                    Appointment.assessment_id == assessment.id,
                    Appointment.doctor_id == user.doctor_id,
                )
                .first()
            )
            if not linked:
                return _json_error("Assessment not linked to your appointments", 403)

        rows = (
            db.query(AssessmentResponse, AssessmentQuestion)
            .join(AssessmentQuestion, AssessmentQuestion.id == AssessmentResponse.question_id)
            .filter(AssessmentResponse.assessment_id == assessment.id)
            .order_by(AssessmentResponse.id.asc())
            .all()
        )
        answers = [
            {
                "question_id": question.id,
                "section": get_question_section(question.question),
                "question": question.question,
                "selected_option": response.selected_option,
                "selected_text": response.selected_text,
                "score": response.score,
            }
            for response, question in rows
        ]
        return JsonResponse(
            {
                "assessment": _serialize_assessment(assessment),
                "patient": {
                    "id": patient.id if patient else None,
                    "child_name": patient.child_name if patient else "",
                    "parent_name": patient.parent_name if patient else "",
                },
                "answers": answers,
            }
        )
    finally:
        db.close()


@require_GET
def booking_page(request: HttpRequest) -> HttpResponse:
    return render(request, "appointment_booking.html")


@require_GET
def appointment_slots_api(request: HttpRequest) -> JsonResponse:
    doctor_id = request.GET.get("doctor_id")
    appointment_date = parse_date(request.GET.get("appointment_date", ""))
    if not doctor_id or not appointment_date:
        return _json_error("doctor_id and appointment_date are required")

    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("admin", "parent"))
        if error:
            return error
        leave = (
            db.query(DoctorLeave)
            .filter(
                DoctorLeave.doctor_id == int(doctor_id),
                DoctorLeave.start_date <= appointment_date,
                DoctorLeave.end_date >= appointment_date,
            )
            .first()
        )
        return JsonResponse(
            {
                "doctor_id": int(doctor_id),
                "appointment_date": appointment_date.isoformat(),
                "on_leave": bool(leave),
                "slots": get_available_slots(db, int(doctor_id), appointment_date),
            }
        )
    finally:
        db.close()


@csrf_exempt
@require_http_methods(["POST"])
def appointment_book_api(request: HttpRequest) -> JsonResponse:
    payload = _parse_json(request)
    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("admin", "parent"))
        if error:
            return error

        patient_id = int(payload.get("patient_id"))
        if user.role == "parent" and user.patient_id != patient_id:
            return _json_error("You can only book for your child", 403)

        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return _json_error("Patient not found", 404)

        assessment = db.query(Assessment).filter(Assessment.id == int(payload.get("assessment_id"))).first()
        if not assessment:
            return _json_error("Assessment not found", 404)
        if assessment.patient_id != patient_id:
            return _json_error("Assessment does not belong to selected patient")

        appointment_date = parse_date(payload.get("appointment_date", ""))
        if not appointment_date:
            return _json_error("Invalid appointment_date")

        try:
            ensure_slot_available(db, int(payload.get("doctor_id")), appointment_date, payload.get("time_slot"))
        except SlotAvailabilityError as exc:
            return _json_error(exc.detail, exc.status_code)

        appointment = Appointment(
            clinic_id=int(payload.get("clinic_id")),
            doctor_id=int(payload.get("doctor_id")),
            patient_id=patient_id,
            assessment_id=assessment.id,
            appointment_date=appointment_date,
            time_slot=payload.get("time_slot"),
            status="scheduled",
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        return JsonResponse(
            {
                "id": appointment.id,
                "clinic_id": appointment.clinic_id,
                "doctor_id": appointment.doctor_id,
                "patient_id": appointment.patient_id,
                "assessment_id": appointment.assessment_id,
                "appointment_date": appointment.appointment_date.isoformat(),
                "time_slot": appointment.time_slot,
                "status": appointment.status,
            },
            status=201,
        )
    finally:
        db.close()


@require_GET
def doctor_dashboard_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("doctor",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        today = date.today()
        appointments = (
            db.query(Appointment, Patient, Assessment)
            .join(Patient, Patient.id == Appointment.patient_id)
            .outerjoin(Assessment, Assessment.id == Appointment.assessment_id)
            .filter(Appointment.doctor_id == user.doctor_id, Appointment.appointment_date == today)
            .order_by(Appointment.time_slot.asc())
            .all()
        )
        return render(request, "doctor_dashboard.html", {"appointments": appointments, "today": today})
    finally:
        db.close()


@require_GET
def doctor_calendar_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("doctor",))
    if redirect_response:
        return redirect_response
    return render(request, "doctor_calendar.html")


@require_GET
def doctor_calendar_data_api(request: HttpRequest) -> JsonResponse:
    month = int(request.GET.get("month", "0"))
    year = int(request.GET.get("year", "0"))
    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("doctor",))
        if error:
            return error

        _, days_in_month = monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, days_in_month)

        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == user.doctor_id,
                Appointment.appointment_date >= start,
                Appointment.appointment_date <= end,
            )
            .all()
        )
        leave_rows = (
            db.query(DoctorLeave)
            .filter(
                DoctorLeave.doctor_id == user.doctor_id,
                DoctorLeave.start_date <= end,
                DoctorLeave.end_date >= start,
            )
            .all()
        )

        by_day = {}
        for i in range(1, days_in_month + 1):
            current_day = date(year, month, i)
            by_day[current_day.isoformat()] = {
                "date": current_day.isoformat(),
                "booked_slots": 0,
                "free_slots": len(DEFAULT_SLOTS),
                "status": "free",
            }

        for appointment in appointments:
            key = appointment.appointment_date.isoformat()
            if appointment.status != "cancelled":
                by_day[key]["booked_slots"] += 1

        for entry in by_day.values():
            entry["free_slots"] = max(0, len(DEFAULT_SLOTS) - entry["booked_slots"])
            if entry["booked_slots"] > 0:
                entry["status"] = "booked"

        for leave in leave_rows:
            current_day = max(leave.start_date, start)
            last_day = min(leave.end_date, end)
            while current_day <= last_day:
                key = current_day.isoformat()
                if key in by_day:
                    by_day[key]["status"] = "leave"
                    by_day[key]["booked_slots"] = 0
                    by_day[key]["free_slots"] = 0
                current_day = current_day.fromordinal(current_day.toordinal() + 1)

        return JsonResponse({"month": month, "year": year, "days": list(by_day.values())})
    finally:
        db.close()


@require_GET
def doctor_day_slots_api(request: HttpRequest) -> JsonResponse:
    selected_date = parse_date(request.GET.get("selected_date", ""))
    if not selected_date:
        return _json_error("selected_date is required")

    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("doctor",))
        if error:
            return error

        appointments = (
            db.query(Appointment, Patient)
            .join(Patient, Patient.id == Appointment.patient_id)
            .filter(
                Appointment.doctor_id == user.doctor_id,
                Appointment.appointment_date == selected_date,
                Appointment.status != "cancelled",
            )
            .order_by(Appointment.time_slot.asc())
            .all()
        )
        booked = [
            {
                "appointment_id": appointment.id,
                "time_slot": appointment.time_slot,
                "patient_id": patient.id,
                "patient_name": patient.child_name,
                "status": appointment.status,
            }
            for appointment, patient in appointments
        ]
        return JsonResponse(
            {
                "date": selected_date.isoformat(),
                "booked": booked,
                "free_slots": get_available_slots(db, user.doctor_id, selected_date),
            }
        )
    finally:
        db.close()


@require_GET
def doctor_appointments_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("doctor",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        appointments = (
            db.query(Appointment)
            .filter(Appointment.doctor_id == user.doctor_id)
            .order_by(Appointment.appointment_date.desc())
            .all()
        )
        return render(request, "doctor_appointments.html", {"appointments": appointments})
    finally:
        db.close()


@require_GET
def doctor_appointment_page(request: HttpRequest, appointment_id: int) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("doctor",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment or appointment.doctor_id != user.doctor_id:
            return redirect("/consultations/doctor/dashboard")

        patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
        assessment = None
        if appointment.assessment_id:
            assessment = db.query(Assessment).filter(Assessment.id == appointment.assessment_id).first()
        consultation = db.query(Consultation).filter(Consultation.appointment_id == appointment.id).first()
        return render(
            request,
            "doctor_consultation.html",
            {
                "appointment": appointment,
                "patient": patient,
                "assessment": assessment,
                "consultation": consultation,
            },
        )
    finally:
        db.close()


@require_GET
def doctor_patient_detail_page(request: HttpRequest, patient_id: int) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("doctor",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return redirect("/consultations/doctor/dashboard")

        linked = (
            db.query(Appointment)
            .filter(Appointment.patient_id == patient.id, Appointment.doctor_id == user.doctor_id)
            .first()
        )
        if not linked:
            return redirect("/consultations/doctor/dashboard")

        assessments = (
            db.query(Assessment)
            .filter(Assessment.patient_id == patient.id)
            .order_by(Assessment.created_at.desc())
            .all()
        )
        return render(request, "doctor_patient_details.html", {"patient": patient, "assessments": assessments})
    finally:
        db.close()


@csrf_exempt
@require_http_methods(["POST"])
def consultation_save_api(request: HttpRequest, appointment_id: int | None = None) -> JsonResponse:
    payload = _parse_json(request)
    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("doctor",))
        if error:
            return error

        target_appointment_id = appointment_id or int(payload.get("appointment_id"))
        appointment = db.query(Appointment).filter(Appointment.id == target_appointment_id).first()
        if not appointment:
            return _json_error("Appointment not found", 404)
        if appointment.doctor_id != user.doctor_id:
            return _json_error("Appointment does not belong to you", 403)

        consultation = db.query(Consultation).filter(Consultation.appointment_id == appointment.id).first()
        if consultation:
            consultation.notes = payload.get("notes", "")
            consultation.diagnosis = payload.get("diagnosis", "")
            consultation.recommendation = payload.get("recommendation", "")
        else:
            consultation = Consultation(
                appointment_id=appointment.id,
                doctor_id=user.doctor_id,
                notes=payload.get("notes", ""),
                diagnosis=payload.get("diagnosis", ""),
                recommendation=payload.get("recommendation", ""),
            )
            db.add(consultation)

        appointment.status = "completed"
        db.commit()
        db.refresh(consultation)
        return JsonResponse(_serialize_consultation(consultation), status=201)
    finally:
        db.close()


@require_GET
def patient_consultations_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("parent",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        rows = (
            db.query(Consultation, Appointment, Assessment)
            .join(Appointment, Appointment.id == Consultation.appointment_id)
            .outerjoin(Assessment, Assessment.id == Appointment.assessment_id)
            .filter(Appointment.patient_id == user.patient_id)
            .order_by(Consultation.created_at.desc())
            .all()
        )
        return render(request, "patient_consultations.html", {"rows": rows})
    finally:
        db.close()


@require_GET
def consultation_detail_api(request: HttpRequest, consultation_id: int) -> JsonResponse:
    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("admin", "doctor", "parent"))
        if error:
            return error

        consultation = db.query(Consultation).filter(Consultation.id == consultation_id).first()
        if not consultation:
            return _json_error("Consultation not found", 404)
        if user.role == "doctor" and consultation.doctor_id != user.doctor_id:
            return _json_error("You can only view your own consultations", 403)
        if user.role == "parent":
            appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()
            if not appointment or appointment.patient_id != user.patient_id:
                return _json_error("You can only view your own consultations", 403)
        return JsonResponse(_serialize_consultation(consultation))
    finally:
        db.close()


@csrf_exempt
@require_http_methods(["POST"])
def report_generate_api(request: HttpRequest) -> JsonResponse:
    consultation_id = request.GET.get("consultation_id")
    if not consultation_id:
        return _json_error("consultation_id is required")

    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("doctor", "admin"))
        if error:
            return error

        consultation = db.query(Consultation).filter(Consultation.id == int(consultation_id)).first()
        if not consultation:
            return _json_error("Consultation not found", 404)
        if user.role == "doctor" and consultation.doctor_id != user.doctor_id:
            return _json_error("You can only generate reports for your consultations", 403)

        appointment = db.query(Appointment).filter(Appointment.id == consultation.appointment_id).first()
        patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first() if appointment else None
        if not patient:
            return _json_error("Patient not found", 404)

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
        return JsonResponse({"report_id": report.id, "file_url": report.file_url})
    finally:
        db.close()


@require_GET
def admin_dashboard_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("admin",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        today = date.today()
        total_assessments = db.query(func.count(Assessment.id)).scalar() or 0
        high_risk_cases = db.query(func.count(Assessment.id)).filter(Assessment.risk_level == "High Risk").scalar() or 0
        appointments_today = (
            db.query(func.count(Appointment.id))
            .filter(Appointment.appointment_date == today, Appointment.status == "scheduled")
            .scalar()
            or 0
        )
        return render(
            request,
            "admin_dashboard.html",
            {
                "total_assessments": total_assessments,
                "high_risk_cases": high_risk_cases,
                "appointments_today": appointments_today,
            },
        )
    finally:
        db.close()


@require_GET
def admin_doctors_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("admin",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        doctors = db.query(Doctor).order_by(Doctor.created_at.desc()).all()
        return render(request, "manage_doctors.html", {"doctors": doctors})
    finally:
        db.close()


@require_GET
def admin_patients_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("admin",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
        return render(request, "manage_patients.html", {"patients": patients})
    finally:
        db.close()


@require_GET
def admin_appointments_page(request: HttpRequest) -> HttpResponse:
    user, redirect_response = _require_page_user(request, ("admin",))
    if redirect_response:
        return redirect_response

    db = SessionLocal()
    try:
        appointments = db.query(Appointment).order_by(Appointment.appointment_date.desc()).all()
        return render(request, "manage_appointments.html", {"appointments": appointments})
    finally:
        db.close()


@csrf_exempt
@require_http_methods(["POST"])
def admin_mark_leave_api(request: HttpRequest, doctor_id: int) -> JsonResponse:
    payload = _parse_json(request)
    db = SessionLocal()
    try:
        user, error = _require_api_user(request, db, ("admin",))
        if error:
            return error

        start_date = parse_date(payload.get("start_date", ""))
        end_date = parse_date(payload.get("end_date", ""))
        if not start_date or not end_date or end_date < start_date:
            return _json_error("Invalid date range")

        leave = DoctorLeave(
            doctor_id=doctor_id,
            start_date=start_date,
            end_date=end_date,
            reason=payload.get("reason", ""),
            status=payload.get("status") or "out_of_office",
        )
        db.add(leave)
        db.commit()
        db.refresh(leave)
        return JsonResponse({"message": "Doctor leave marked", "leave_id": leave.id})
    finally:
        db.close()
