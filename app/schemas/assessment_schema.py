from datetime import datetime

from pydantic import BaseModel


class AssessmentQuestionOut(BaseModel):
    id: int
    question: str
    section: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    score_a: int
    score_b: int
    score_c: int
    score_d: int

    class Config:
        from_attributes = True


class AssessmentAnswer(BaseModel):
    question_id: int
    selected_option: str


class AssessmentSubmit(BaseModel):
    patient_id: int | None = None
    clinic_id: int
    answers: list[AssessmentAnswer]
    parent_name: str | None = None
    child_name: str | None = None
    child_age: int | None = None
    email: str | None = None
    phone: str | None = None


class AssessmentOut(BaseModel):
    id: int
    patient_id: int
    clinic_id: int
    score: int
    risk_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class AssessmentSubmitOut(AssessmentOut):
    section_scores: dict[str, int]
