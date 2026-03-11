import os
import tempfile

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.models.assessment import Assessment
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.utils.cloudinary_utils import upload_file


def generate_consultation_report(
    patient: Patient,
    assessment: Assessment | None,
    consultation: Consultation,
) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file.close()

    c = canvas.Canvas(temp_file.name, pagesize=A4)
    y = 800
    lines = [
        "Child Autism Screening Consultation Report",
        "",
        f"Patient (Child): {patient.child_name}",
        f"Parent Name: {patient.parent_name}",
        f"Child Age: {patient.child_age}",
        f"Patient Email: {patient.email}",
        "",
    ]

    if assessment:
        lines.extend(
            [
                f"Assessment Score: {assessment.score}",
                f"Risk Level: {assessment.risk_level}",
                "",
            ]
        )

    lines.extend(
        [
            f"Diagnosis: {consultation.diagnosis}",
            "",
            "Doctor Notes:",
            consultation.notes,
            "",
            "Recommendations:",
            consultation.recommendation,
        ]
    )

    for line in lines:
        c.drawString(50, y, line[:120])
        y -= 20
        if y < 60:
            c.showPage()
            y = 800

    c.save()

    try:
        return upload_file(temp_file.name)
    finally:
        os.unlink(temp_file.name)
