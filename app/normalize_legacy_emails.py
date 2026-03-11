from app.database import SessionLocal
from app.models import Appointment, Assessment, Consultation, Doctor, Patient, User
from app.models.doctor import DoctorLeave


def to_com(email: str) -> str:
    return email.replace('@clinic.local', '@clinic.com')


def normalize_doctors(db):
    rows = db.query(Doctor).filter(Doctor.email.like('%@clinic.local')).all()
    for row in rows:
        target_email = to_com(row.email)
        target = db.query(Doctor).filter(Doctor.email == target_email).first()
        if not target:
            row.email = target_email
            continue

        db.query(Appointment).filter(Appointment.doctor_id == row.id).update({Appointment.doctor_id: target.id})
        db.query(Consultation).filter(Consultation.doctor_id == row.id).update({Consultation.doctor_id: target.id})
        db.query(User).filter(User.doctor_id == row.id).update({User.doctor_id: target.id})
        db.query(DoctorLeave).filter(DoctorLeave.doctor_id == row.id).update({DoctorLeave.doctor_id: target.id})
        db.delete(row)


def normalize_patients(db):
    rows = db.query(Patient).filter(Patient.email.like('%@clinic.local')).all()
    for row in rows:
        target_email = to_com(row.email)
        target = db.query(Patient).filter(Patient.email == target_email).first()
        if not target:
            row.email = target_email
            continue

        db.query(Appointment).filter(Appointment.patient_id == row.id).update({Appointment.patient_id: target.id})
        db.query(Assessment).filter(Assessment.patient_id == row.id).update({Assessment.patient_id: target.id})
        db.query(User).filter(User.patient_id == row.id).update({User.patient_id: target.id})
        db.delete(row)


def normalize_users(db):
    rows = db.query(User).filter(User.email.like('%@clinic.local')).all()
    for row in rows:
        target_email = to_com(row.email)
        target = db.query(User).filter(User.email == target_email).first()
        if target:
            db.delete(row)
        else:
            row.email = target_email


def main():
    db = SessionLocal()
    try:
        normalize_doctors(db)
        normalize_patients(db)
        normalize_users(db)
        db.commit()
        print('Legacy email normalization complete.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
