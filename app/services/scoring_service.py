from app.models.assessment import AssessmentQuestion


def resolve_option_score(question: AssessmentQuestion, selected_option: str) -> int:
    option_map = {
        "a": question.score_a,
        "b": question.score_b,
        "c": question.score_c,
        "d": question.score_d,
    }
    key = selected_option.lower().strip()
    if key not in option_map:
        raise ValueError(f"Invalid option: {selected_option}")
    return option_map[key]


def calculate_risk(score: int, max_score: int | None = None) -> str:
    # For long questionnaires, classify by percentage bands.
    if max_score and max_score > 0:
        ratio = score / max_score
        if ratio < 0.35:
            return "Low Risk"
        if ratio <= 0.65:
            return "Moderate Risk"
        return "High Risk"

    if score < 10:
        return "Low Risk"
    if score <= 20:
        return "Moderate Risk"
    return "High Risk"
