"""Backward-compatible report utility wrapper."""

from .models import Assessment
from .services.report_generator import generate_assessment_report


def generate_report(assessment_id: int) -> dict:
    assessment = Assessment.objects.get(id=assessment_id)
    return generate_assessment_report(assessment)
