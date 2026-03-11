from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    parent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    child_name: Mapped[str] = mapped_column(String(255), nullable=False)
    child_age: Mapped[int] = mapped_column(Integer, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="patients")
    assessments = relationship("Assessment", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    user = relationship("User", back_populates="patient", uselist=False)
