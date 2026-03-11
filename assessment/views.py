"""API views for questionnaire retrieval and assessment lifecycle."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assessment, AssessmentDraft, Question, Response as AssessmentResponse
from .serializers import (
    AssessmentDraftSerializer,
    AssessmentReportSerializer,
    QuestionSerializer,
    QuestionSectionSerializer,
    SaveDraftSerializer,
    SubmitAssessmentSerializer,
    build_responses,
)
from .services.report_generator import generate_assessment_report


class ScreeningGUIView(TemplateView):
    """Frontend application shell for the screening workflow."""

    template_name = "assessment/gui.html"


class LandingView(TemplateView):
    """Public landing page for the hosted Django site."""

    template_name = "assessment/landing.html"


class ParentPortalView(TemplateView):
    """Simple parent portal entry page."""

    template_name = "assessment/parent_portal.html"


class QuestionListAPIView(APIView):
    """Returns all active questions with options and scores."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        child_age_months = request.query_params.get("child_age_months")
        queryset = Question.objects.select_related("category").prefetch_related("option_set")

        if child_age_months is not None:
            try:
                age = int(child_age_months)
            except ValueError:
                return Response(
                    {"detail": "child_age_months must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = queryset.filter(
                Q(min_age_months__isnull=True) | Q(min_age_months__lte=age),
                Q(max_age_months__isnull=True) | Q(max_age_months__gte=age),
            )

        serializer = QuestionSerializer(queryset, many=True)
        return Response(serializer.data)


class QuestionSectionListAPIView(APIView):
    """Returns questions grouped by category for section-based UIs."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        child_age_months = request.query_params.get("child_age_months")
        queryset = Question.objects.select_related("category").prefetch_related("option_set")

        if child_age_months is not None:
            try:
                age = int(child_age_months)
            except ValueError:
                return Response(
                    {"detail": "child_age_months must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(
                Q(min_age_months__isnull=True) | Q(min_age_months__lte=age),
                Q(max_age_months__isnull=True) | Q(max_age_months__gte=age),
            )

        grouped: dict[str, list[Question]] = {}
        for question in queryset:
            grouped.setdefault(question.category.name, []).append(question)

        payload = [
            {"section": section_name, "questions": QuestionSerializer(items, many=True).data}
            for section_name, items in grouped.items()
        ]
        # Return serialized payload directly; validating as input drops read-only ids.
        return Response(payload)


class SubmitAssessmentAPIView(APIView):
    """Persists responses and returns a full risk report payload."""
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = SubmitAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        assessment = Assessment.objects.create(
            name=validated["name"],
            respondent_name=validated.get("respondent_name", ""),
            respondent_role=validated.get("respondent_role", ""),
            respondent_email=validated.get("respondent_email", ""),
            child_age_months=validated.get("child_age_months"),
            metadata=validated.get("metadata", {}),
        )

        response_rows = build_responses(validated["responses"], assessment)
        AssessmentResponse.objects.bulk_create(response_rows)

        report_payload = generate_assessment_report(assessment)
        response_serializer = AssessmentReportSerializer(data=report_payload)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class AssessmentReportAPIView(APIView):
    """Fetch report for an existing assessment."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, assessment_id: int):
        assessment = get_object_or_404(Assessment, id=assessment_id)
        report_payload = generate_assessment_report(assessment)
        serializer = AssessmentReportSerializer(data=report_payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class AssessmentDraftAPIView(APIView):
    """Create or update draft payloads for resuming assessment later."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SaveDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        draft_id = data.get("draft_id")

        if draft_id:
            draft = get_object_or_404(AssessmentDraft, id=draft_id)
            for field in (
                "name",
                "respondent_name",
                "respondent_role",
                "respondent_email",
                "child_age_months",
            ):
                if field in data:
                    setattr(draft, field, data[field])
            draft.metadata = data.get("metadata", draft.metadata)
            draft.responses = data.get("responses", draft.responses)
            draft.save()
        else:
            draft = AssessmentDraft.objects.create(
                name=data["name"],
                respondent_name=data.get("respondent_name", ""),
                respondent_role=data.get("respondent_role", ""),
                respondent_email=data.get("respondent_email", ""),
                child_age_months=data.get("child_age_months"),
                metadata=data.get("metadata", {}),
                responses=data.get("responses", {}),
            )

        return Response(AssessmentDraftSerializer(draft).data, status=status.HTTP_200_OK)


class AssessmentDraftDetailAPIView(APIView):
    """Load an existing assessment draft by id."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, draft_id: int):
        draft = get_object_or_404(AssessmentDraft, id=draft_id)
        return Response(AssessmentDraftSerializer(draft).data)
