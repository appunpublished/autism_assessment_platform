from app.routes.admin_routes import router as admin_router
from app.routes.appointment_routes import router as appointment_router
from app.routes.assessment_routes import router as assessment_router
from app.routes.auth_routes import router as auth_router
from app.routes.clinic_routes import router as clinic_router
from app.routes.consultation_routes import router as consultation_router
from app.routes.doctor_routes import router as doctor_router
from app.routes.patient_routes import router as patient_router
from app.routes.report_routes import router as report_router

__all__ = [
    "admin_router",
    "appointment_router",
    "assessment_router",
    "auth_router",
    "clinic_router",
    "consultation_router",
    "doctor_router",
    "patient_router",
    "report_router",
]
