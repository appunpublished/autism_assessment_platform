from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentResponse
from app.models.patient import Patient
from app.models.user import User
from app.schemas.assessment_schema import AssessmentOut, AssessmentQuestionOut, AssessmentSubmit, AssessmentSubmitOut
from app.services.question_catalog import get_question_section
from app.services.scoring_service import calculate_risk, resolve_option_score
from app.utils.auth_utils import get_current_user, get_optional_current_user, require_roles

router = APIRouter(prefix="/assessment", tags=["Assessment"])
templates = Jinja2Templates(directory="templates")


@router.get("/patient/{patient_id}", response_model=list[AssessmentOut])
def patient_assessments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor", "parent")),
):
    if current_user.role == "parent" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="You can only view your own child assessments")

    return (
        db.query(Assessment)
        .filter(Assessment.patient_id == patient_id)
        .order_by(Assessment.created_at.desc())
        .all()
    )


@router.get("/questions", response_model=list[AssessmentQuestionOut])
def get_questions(db: Session = Depends(get_db)):
    rows = db.query(AssessmentQuestion).order_by(AssessmentQuestion.id.asc()).all()
    result: list[AssessmentQuestionOut] = []
    for row in rows:
        result.append(
            AssessmentQuestionOut(
                id=row.id,
                question=row.question,
                section=get_question_section(row.question),
                option_a=row.option_a,
                option_b=row.option_b,
                option_c=row.option_c,
                option_d=row.option_d,
                score_a=row.score_a,
                score_b=row.score_b,
                score_c=row.score_c,
                score_d=row.score_d,
            )
        )
    return result


@router.post("/submit", response_model=AssessmentSubmitOut)
def submit_assessment(
    payload: AssessmentSubmit,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user and current_user.role not in {"admin", "parent"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    patient = None
    if payload.patient_id:
        patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if current_user and current_user.role == "parent" and current_user.patient_id != payload.patient_id:
            raise HTTPException(status_code=403, detail="You can only submit your own child assessment")
        if payload.clinic_id != patient.clinic_id:
            raise HTTPException(status_code=400, detail="Clinic mismatch with patient record")
    else:
        required_fields = {
            "parent_name": payload.parent_name,
            "child_name": payload.child_name,
            "child_age": payload.child_age,
            "email": payload.email,
            "phone": payload.phone,
        }
        missing = [field for field, value in required_fields.items() if value in {None, ""}]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing)}")

        patient = db.query(Patient).filter(Patient.email == payload.email).first()
        if patient:
            if patient.clinic_id != payload.clinic_id:
                raise HTTPException(status_code=400, detail="Existing patient belongs to a different clinic")
            patient.parent_name = payload.parent_name or patient.parent_name
            patient.child_name = payload.child_name or patient.child_name
            patient.child_age = int(payload.child_age or patient.child_age)
            patient.phone = payload.phone or patient.phone
        else:
            patient = Patient(
                clinic_id=payload.clinic_id,
                parent_name=payload.parent_name or "",
                child_name=payload.child_name or "",
                child_age=int(payload.child_age or 0),
                email=payload.email or "",
                phone=payload.phone or "",
            )
            db.add(patient)
            db.flush()

    score = 0
    max_score = 0
    section_scores: dict[str, int] = {}
    for answer in payload.answers:
        question = db.query(AssessmentQuestion).filter(AssessmentQuestion.id == answer.question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail=f"Question {answer.question_id} not found")
        try:
            answer_score = resolve_option_score(question, answer.selected_option)
            score += answer_score
            max_score += max(question.score_a, question.score_b, question.score_c, question.score_d)
            section = get_question_section(question.question)
            section_scores[section] = section_scores.get(section, 0) + answer_score
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    assessment = Assessment(
        patient_id=payload.patient_id,
        clinic_id=payload.clinic_id,
        score=score,
        risk_level=calculate_risk(score, max_score=max_score),
    )
    db.add(assessment)
    db.flush()

    for answer in payload.answers:
        question = db.query(AssessmentQuestion).filter(AssessmentQuestion.id == answer.question_id).first()
        selected_option = answer.selected_option.lower().strip()
        selected_text = getattr(question, f"option_{selected_option}")
        selected_score = resolve_option_score(question, selected_option)
        db.add(
            AssessmentResponse(
                assessment_id=assessment.id,
                question_id=question.id,
                selected_option=selected_option,
                selected_text=selected_text,
                score=selected_score,
            )
        )

    db.commit()
    db.refresh(assessment)
    return AssessmentSubmitOut(
        id=assessment.id,
        patient_id=assessment.patient_id,
        clinic_id=assessment.clinic_id,
        score=assessment.score,
        risk_level=assessment.risk_level,
        created_at=assessment.created_at,
        section_scores=section_scores,
    )


@router.get("/{assessment_id}/details")
def assessment_details(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor", "parent")),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    patient = db.query(Patient).filter(Patient.id == assessment.patient_id).first()
    if current_user.role == "parent" and current_user.patient_id != assessment.patient_id:
        raise HTTPException(status_code=403, detail="You can only view your own child assessments")
    if current_user.role == "doctor":
        linked = (
            db.query(Appointment)
            .filter(
                Appointment.assessment_id == assessment.id,
                Appointment.doctor_id == current_user.doctor_id,
            )
            .first()
        )
        if not linked:
            raise HTTPException(status_code=403, detail="Assessment not linked to your appointments")

    responses = (
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
        for response, question in responses
    ]

    return {
        "assessment": {
            "id": assessment.id,
            "score": assessment.score,
            "risk_level": assessment.risk_level,
            "created_at": assessment.created_at,
        },
        "patient": {
            "id": patient.id if patient else None,
            "child_name": patient.child_name if patient else "",
            "parent_name": patient.parent_name if patient else "",
        },
        "answers": answers,
    }


@router.get("/page", response_class=HTMLResponse)
def assessment_page(request: Request):
    return templates.TemplateResponse("assessment.html", {"request": request})


@router.get("/result/{assessment_id}", response_class=HTMLResponse)
def assessment_result_page(assessment_id: int, request: Request, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    recommendation = {
        "Low Risk": "Continue developmental observation and periodic screening.",
        "Moderate Risk": "Schedule consultation for clinical developmental evaluation.",
        "High Risk": "Urgent consultation with specialist is recommended.",
    }[assessment.risk_level]

    return templates.TemplateResponse(
        "assessment_result.html",
        {
            "request": request,
            "assessment": assessment,
            "recommendation": recommendation,
        },
    )
