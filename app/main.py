from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import AssessmentQuestion, Clinic, User
from app.routes import (
    admin_router,
    appointment_router,
    assessment_router,
    auth_router,
    clinic_router,
    consultation_router,
    doctor_router,
    patient_router,
    report_router,
)
from app.services.question_catalog import get_seed_questions
from app.utils.auth_utils import hash_password

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).first()
        if not clinic:
            clinic = Clinic(name="Hope Neuro Clinic", address="MG Road", phone="+91-9000000000")
            db.add(clinic)
            db.flush()

        default_admin = db.query(User).filter(User.email == settings.default_admin_email).first()
        if not default_admin:
            db.add(
                User(
                    email=settings.default_admin_email,
                    password_hash=hash_password(settings.default_admin_password),
                    role="admin",
                    clinic_id=clinic.id,
                )
            )

        existing_questions = {q for (q,) in db.query(AssessmentQuestion.question).all()}
        for item in get_seed_questions():
            if item["question"] not in existing_questions:
                db.add(AssessmentQuestion(**item))

        db.commit()
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


app.include_router(auth_router)
app.include_router(clinic_router)
app.include_router(doctor_router)
app.include_router(patient_router)
app.include_router(assessment_router)
app.include_router(appointment_router)
app.include_router(consultation_router)
app.include_router(admin_router)
app.include_router(report_router)
