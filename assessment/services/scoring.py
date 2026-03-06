"""Scoring service for autism screening assessments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from assessment.models import (
    AgeBandCategoryWeight,
    AgeScoringBand,
    Assessment,
    Response,
)


@dataclass(frozen=True)
class RiskBand:
    label: str
    min_score: int
    max_score: int | None = None

    def contains(self, score: int) -> bool:
        if score < self.min_score:
            return False
        if self.max_score is None:
            return True
        return score <= self.max_score


RISK_BANDS = (
    RiskBand(label="Low", min_score=0, max_score=30),
    RiskBand(label="Mild", min_score=31, max_score=60),
    RiskBand(label="Moderate", min_score=61, max_score=100),
    RiskBand(label="High", min_score=101, max_score=None),
)


def weighted_value(response: Response) -> int:
    """Calculate weighted value for a single response."""
    question = response.question
    category = question.category
    return int(round(response.selected_option.score * question.weight * category.weight))


def get_age_band_for_months(age_months: int | None) -> AgeScoringBand | None:
    """Return matching age scoring band for provided age in months."""
    if age_months is None:
        return None
    return (
        AgeScoringBand.objects.filter(
            min_age_months__lte=age_months,
            max_age_months__gte=age_months,
        )
        .order_by("min_age_months")
        .first()
    )


def age_band_category_multiplier(age_band: AgeScoringBand | None, category_id: int) -> float:
    """Fetch category multiplier for a given age band; fallback to 1.0."""
    if age_band is None:
        return 1.0
    weight = AgeBandCategoryWeight.objects.filter(
        age_band=age_band,
        category_id=category_id,
    ).first()
    return weight.multiplier if weight else 1.0


def category_scores_for_assessment(assessment_id: int) -> Dict[str, int]:
    """Return score totals grouped by category name."""
    responses = Response.objects.select_related(
        "question__category", "selected_option"
    ).filter(assessment_id=assessment_id)

    assessment = Assessment.objects.filter(id=assessment_id).first()
    age_band = get_age_band_for_months(
        assessment.child_age_months if assessment else None
    )

    category_scores: Dict[str, int] = {}
    for response in responses:
        category_name = response.question.category.name
        multiplier = age_band_category_multiplier(age_band, response.question.category_id)
        score = int(round(weighted_value(response) * multiplier))
        category_scores[category_name] = category_scores.get(category_name, 0) + score

    return category_scores


def calculate_total_score(assessment_id: int) -> int:
    """Calculate weighted total score for an assessment."""
    return sum(category_scores_for_assessment(assessment_id).values())


def derive_risk_level(score: int) -> str:
    """Map numeric score to configured risk level."""
    for band in RISK_BANDS:
        if band.contains(score):
            return band.label
    return "Unknown"


def derive_risk_level_for_assessment(score: int, assessment: Assessment) -> str:
    """Use age-band thresholds when available; fallback to default bands."""
    age_band = get_age_band_for_months(assessment.child_age_months)
    if age_band is None:
        return derive_risk_level(score)
    if score <= age_band.low_max:
        return "Low"
    if score <= age_band.mild_max:
        return "Mild"
    if score <= age_band.moderate_max:
        return "Moderate"
    return "High"


def persist_assessment_score(assessment: Assessment) -> Assessment:
    """Compute and persist score/risk_level on assessment."""
    score = calculate_total_score(assessment.id)
    assessment.total_score = score
    assessment.risk_level = derive_risk_level_for_assessment(score, assessment)
    assessment.save(update_fields=["total_score", "risk_level", "updated_at"])
    return assessment
