"""Question seeding helpers for local/dev environments."""

from .models import QuestionCategory, Question, Option
from .question_bank import QUESTION_BANK, OPTIONS


def seed_questions():
    for index, q in enumerate(QUESTION_BANK, start=1):
        category, _ = QuestionCategory.objects.get_or_create(
            name=q["category"]
        )

        question, _ = Question.objects.get_or_create(
            text=q["question"],
            category=category,
            defaults={"display_order": index},
        )

        for option in OPTIONS:
            Option.objects.get_or_create(
                question=question,
                text=option["text"],
                score=option["score"]
            )

    print("Questions inserted successfully")
