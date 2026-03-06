"""Serializers for questionnaire retrieval and assessment submission."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import Assessment, AssessmentDraft, Option, Question, Response


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("id", "text", "score")


class QuestionSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name")
    options = OptionSerializer(many=True, source="option_set")

    class Meta:
        model = Question
        fields = ("id", "category", "text", "options")


class QuestionSectionSerializer(serializers.Serializer):
    section = serializers.CharField()
    questions = QuestionSerializer(many=True)


class AssessmentResponseInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    option_id = serializers.IntegerField()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        question_id = attrs["question_id"]
        option_id = attrs["option_id"]

        if not Question.objects.filter(id=question_id).exists():
            raise serializers.ValidationError({"question_id": "Invalid question_id."})

        if not Option.objects.filter(id=option_id).exists():
            raise serializers.ValidationError({"option_id": "Invalid option_id."})

        if not Option.objects.filter(id=option_id, question_id=question_id).exists():
            raise serializers.ValidationError(
                "option_id does not belong to the provided question_id."
            )

        return attrs


class SubmitAssessmentSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    respondent_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    respondent_role = serializers.CharField(max_length=100, required=False, allow_blank=True)
    respondent_email = serializers.EmailField(required=False, allow_blank=True)
    child_age_months = serializers.IntegerField(required=False, min_value=0)
    metadata = serializers.JSONField(required=False)
    responses = AssessmentResponseInputSerializer(many=True, min_length=1)

    def validate_responses(
        self, value: list[dict[str, int]]
    ) -> list[dict[str, int]]:
        question_ids = [item["question_id"] for item in value]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError(
                "Each question can only be answered once per assessment."
            )
        return value


class AssessmentReportSerializer(serializers.Serializer):
    assessment_id = serializers.IntegerField()
    score = serializers.IntegerField()
    risk_level = serializers.CharField()
    age_band = serializers.CharField(required=False)
    category_scores = serializers.DictField(child=serializers.IntegerField())
    recommendation = serializers.CharField()


class AssessmentExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = (
            "id",
            "name",
            "respondent_name",
            "respondent_role",
            "respondent_email",
            "child_age_months",
            "metadata",
            "total_score",
            "risk_level",
            "created_at",
            "updated_at",
        )


class AssessmentDraftSerializer(serializers.ModelSerializer):
    draft_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = AssessmentDraft
        fields = (
            "draft_id",
            "name",
            "respondent_name",
            "respondent_role",
            "respondent_email",
            "child_age_months",
            "metadata",
            "responses",
            "created_at",
            "updated_at",
        )


class SaveDraftSerializer(serializers.Serializer):
    draft_id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=200)
    respondent_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    respondent_role = serializers.CharField(max_length=100, required=False, allow_blank=True)
    respondent_email = serializers.EmailField(required=False, allow_blank=True)
    child_age_months = serializers.IntegerField(required=False, min_value=0, allow_null=True)
    metadata = serializers.JSONField(required=False)
    responses = serializers.DictField(
        child=serializers.IntegerField(min_value=1), required=False
    )


def build_responses(validated_data: list[dict[str, int]], assessment: Assessment) -> list[Response]:
    """Create in-memory response objects for bulk insert."""
    return [
        Response(
            assessment=assessment,
            question_id=item["question_id"],
            selected_option_id=item["option_id"],
        )
        for item in validated_data
    ]
