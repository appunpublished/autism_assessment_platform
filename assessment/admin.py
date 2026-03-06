import csv
from typing import Iterable

from django.contrib import admin
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.utils import timezone

from .models import (
    AgeBandCategoryWeight,
    AgeScoringBand,
    Assessment,
    AssessmentDraft,
    Option,
    Question,
    QuestionCategory,
    Response,
)


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "weight", "created_at", "updated_at")
    search_fields = ("name",)
    list_editable = ("weight",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "short_text", "category", "display_order", "weight", "updated_at")
    list_filter = ("category",)
    search_fields = ("text",)
    list_editable = ("display_order", "weight")
    inlines = [OptionInline]

    @staticmethod
    def short_text(obj: Question) -> str:
        return f"{obj.text[:70]}..." if len(obj.text) > 70 else obj.text


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "text", "score", "updated_at")
    list_filter = ("question__category",)
    search_fields = ("text", "question__text")


@admin.action(description="Export selected assessments as CSV")
def export_assessments_csv(modeladmin, request, queryset: Iterable[Assessment]):
    response = HttpResponse(content_type="text/csv")
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="assessments_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "id",
            "name",
            "respondent_name",
            "respondent_role",
            "respondent_email",
            "child_age_months",
            "total_score",
            "risk_level",
            "created_at",
        ]
    )

    for assessment in queryset:
        writer.writerow(
            [
                assessment.id,
                assessment.name,
                assessment.respondent_name,
                assessment.respondent_role,
                assessment.respondent_email,
                assessment.child_age_months,
                assessment.total_score,
                assessment.risk_level,
                assessment.created_at,
            ]
        )

    return response


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "respondent_name",
        "child_age_months",
        "total_score",
        "risk_level",
        "created_at",
    )
    search_fields = ("name", "respondent_name", "respondent_email")
    list_filter = ("risk_level", "created_at")
    readonly_fields = ("created_at", "updated_at")
    actions = [export_assessments_csv]

    def changelist_view(self, request, extra_context=None):
        stats = Assessment.objects.aggregate(
            total_assessments=Count("id"),
            avg_score=Avg("total_score"),
        )
        risk_counts = dict(
            Assessment.objects.values_list("risk_level").annotate(count=Count("id"))
        )
        context = extra_context or {}
        context["assessment_stats"] = {
            "total_assessments": stats["total_assessments"] or 0,
            "avg_score": round(stats["avg_score"] or 0, 2),
            "risk_counts": risk_counts,
        }
        return super().changelist_view(request, extra_context=context)


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "assessment", "question", "selected_option", "created_at")
    list_filter = ("question__category", "assessment__risk_level")
    search_fields = ("assessment__name", "question__text", "selected_option__text")


@admin.register(AssessmentDraft)
class AssessmentDraftAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "respondent_name", "respondent_role", "updated_at")
    search_fields = ("name", "respondent_name", "respondent_email")


@admin.register(AgeScoringBand)
class AgeScoringBandAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "min_age_months",
        "max_age_months",
        "low_max",
        "mild_max",
        "moderate_max",
    )
    list_editable = ("low_max", "mild_max", "moderate_max")


@admin.register(AgeBandCategoryWeight)
class AgeBandCategoryWeightAdmin(admin.ModelAdmin):
    list_display = ("id", "age_band", "category", "multiplier", "updated_at")
    list_filter = ("age_band", "category")
    list_editable = ("multiplier",)
