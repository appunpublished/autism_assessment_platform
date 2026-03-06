"""Backward-compatible import surface for scoring helpers."""

from .services.scoring import (
    calculate_total_score as calculate_score,
    derive_risk_level as risk_level,
)
