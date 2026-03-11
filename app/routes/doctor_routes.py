from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor_schema import DoctorCreate, DoctorOut
from app.utils.auth_utils import get_current_user, hash_password, require_roles

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("", response_model=list[DoctorOut])
def list_doctors(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Doctor).all()


@router.post("", response_model=DoctorOut)
def create_doctor(
    payload: DoctorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    if db.query(Doctor).filter(Doctor.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Doctor email already exists")

    doctor = Doctor(**payload.model_dump(exclude={"password"}))
    db.add(doctor)
    db.flush()

    if payload.password:
        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            role="doctor",
            clinic_id=payload.clinic_id,
            doctor_id=doctor.id,
        )
        db.add(user)

    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor
