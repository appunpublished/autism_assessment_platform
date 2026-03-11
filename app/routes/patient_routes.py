from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient_schema import PatientCreate, PatientOut
from app.utils.auth_utils import get_current_user, hash_password, require_roles

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "doctor", "parent"))):
    query = db.query(Patient)
    if current_user.role == "parent":
        query = query.filter(Patient.id == current_user.patient_id)
    return query.order_by(Patient.created_at.desc()).all()


@router.post("", response_model=PatientOut)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if db.query(Patient).filter(Patient.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Patient email already exists")

    patient = Patient(**payload.model_dump(exclude={"password"}))
    db.add(patient)
    db.flush()

    if payload.password:
        parent_user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            role="parent",
            clinic_id=payload.clinic_id,
            patient_id=patient.id,
        )
        db.add(parent_user)

    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "doctor", "parent")),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if current_user.role == "parent" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="You can only view your child data")

    return patient
