"""Assessment report generation service."""

from __future__ import annotations

from assessment.models import Assessment
from assessment.services.scoring import (
    category_scores_for_assessment,
    derive_risk_level,
    get_age_band_for_months,
    persist_assessment_score,
)


RECOMMENDATIONS = {
    "Low": "Low screening risk. Continue developmental observation and routine pediatric follow-up.",
    "Mild": "Mild screening risk. Discuss findings with your pediatrician and monitor concerns.",
    "Moderate": "Consider consulting a developmental pediatrician.",
    "High": "High screening risk. Seek a comprehensive developmental evaluation promptly.",
}


def recommendation_for_risk(risk_level: str) -> str:
    """Return recommendation text for a given risk level."""
    return RECOMMENDATIONS.get(
        risk_level,
        "This is a screening result only. Consult a qualified clinician for diagnosis.",
    )


def generate_assessment_report(assessment: Assessment) -> dict:
    """Build report payload returned by API endpoints."""
    assessment = persist_assessment_score(assessment)
    category_scores = category_scores_for_assessment(assessment.id)
    risk_level = derive_risk_level(assessment.total_score)
    age_band = get_age_band_for_months(assessment.child_age_months)

    return {
        "assessment_id": assessment.id,
        "score": assessment.total_score,
        "risk_level": risk_level,
        "age_band": age_band.name if age_band else "Unspecified",
        "category_scores": category_scores,
        "recommendation": recommendation_for_risk(risk_level),
    }
