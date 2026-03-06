from django.urls import path

from .views import (
    AssessmentDraftAPIView,
    AssessmentDraftDetailAPIView,
    AssessmentReportAPIView,
    QuestionListAPIView,
    QuestionSectionListAPIView,
    SubmitAssessmentAPIView,
)

urlpatterns = [
    path("questions/", QuestionListAPIView.as_view(), name="questions"),
    path("questions/sections/", QuestionSectionListAPIView.as_view(), name="questions-sections"),
    path("submit-assessment/", SubmitAssessmentAPIView.as_view(), name="submit-assessment"),
    path("assessment-drafts/", AssessmentDraftAPIView.as_view(), name="assessment-drafts"),
    path(
        "assessment-drafts/<int:draft_id>/",
        AssessmentDraftDetailAPIView.as_view(),
        name="assessment-draft-detail",
    ),
    path(
        "assessments/<int:assessment_id>/report/",
        AssessmentReportAPIView.as_view(),
        name="assessment-report",
    ),
]
