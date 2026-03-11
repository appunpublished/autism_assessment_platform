from assessment.question_bank import QUESTION_BANK

SECTION_ORDER = [
    "Social Communication",
    "Repetitive Behaviour",
    "Sensory Sensitivity",
    "Development",
]

QUESTION_SECTION_MAP = {item["question"]: item["category"] for item in QUESTION_BANK}


def get_seed_questions() -> list[dict]:
    seed = []
    for item in QUESTION_BANK:
        seed.append(
            {
                "question": item["question"],
                "option_a": "Never",
                "option_b": "Rarely",
                "option_c": "Sometimes",
                "option_d": "Often",
                "score_a": 0,
                "score_b": 1,
                "score_c": 2,
                "score_d": 3,
            }
        )
    return seed


def get_question_section(question_text: str) -> str:
    return QUESTION_SECTION_MAP.get(question_text, "General")
