from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    doctors = relationship("Doctor", back_populates="clinic", cascade="all,delete")
    patients = relationship("Patient", back_populates="clinic", cascade="all,delete")
    assessments = relationship("Assessment", back_populates="clinic", cascade="all,delete")
    appointments = relationship("Appointment", back_populates="clinic", cascade="all,delete")
    users = relationship("User", back_populates="clinic", cascade="all,delete")
