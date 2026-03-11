from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id", ondelete="SET NULL"), nullable=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="users")
    doctor = relationship("Doctor", back_populates="user")
    patient = relationship("Patient", back_populates="user")
