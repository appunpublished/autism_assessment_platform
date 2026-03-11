from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clinic import Clinic
from app.schemas.clinic_schema import ClinicOut

router = APIRouter(prefix="/clinics", tags=["Clinics"])


@router.get("", response_model=list[ClinicOut])
def list_clinics(db: Session = Depends(get_db)):
    return db.query(Clinic).order_by(Clinic.name.asc()).all()
