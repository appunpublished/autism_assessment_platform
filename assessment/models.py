from django.db import models


class TimeStampedModel(models.Model):
    """Reusable created/updated timestamps for auditability."""

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class QuestionCategory(TimeStampedModel):
    """Logical group for screening questions."""

    name = models.CharField(max_length=200, unique=True)
    weight = models.FloatField(default=1.0, help_text="Optional category scoring weight.")

    def __str__(self):
        return self.name


class Question(TimeStampedModel):
    """Single screening question with ordering and optional weighting."""

    text = models.TextField()
    category = models.ForeignKey(QuestionCategory, on_delete=models.CASCADE)
    weight = models.FloatField(default=1.0, help_text="Optional per-question scoring weight.")
    display_order = models.PositiveIntegerField(default=0)
    min_age_months = models.PositiveIntegerField(null=True, blank=True)
    max_age_months = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.text

    class Meta:
        ordering = ["display_order", "id"]


class Option(TimeStampedModel):
    """Answer option carrying a base score."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    score = models.IntegerField()

    def __str__(self):
        return f"{self.text} ({self.score})"

    class Meta:
        ordering = ["score", "id"]


class Assessment(TimeStampedModel):
    """A single submitted screening run."""

    name = models.CharField(max_length=200)
    respondent_name = models.CharField(max_length=200, blank=True, default="")
    respondent_role = models.CharField(max_length=100, blank=True, default="")
    respondent_email = models.EmailField(blank=True, default="")
    child_age_months = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    total_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=50, blank=True, default="")


class Response(TimeStampedModel):
    """Selected option for one question within an assessment."""

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "question"],
                name="unique_question_per_assessment",
            )
        ]


class AssessmentDraft(TimeStampedModel):
    """Persisted partial assessment state for resume workflows."""

    name = models.CharField(max_length=200)
    respondent_name = models.CharField(max_length=200, blank=True, default="")
    respondent_role = models.CharField(max_length=100, blank=True, default="")
    respondent_email = models.EmailField(blank=True, default="")
    child_age_months = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    responses = models.JSONField(default=dict, blank=True)


class AgeScoringBand(TimeStampedModel):
    """Age-specific scoring configuration with optional risk thresholds."""

    name = models.CharField(max_length=100, unique=True)
    min_age_months = models.PositiveIntegerField()
    max_age_months = models.PositiveIntegerField()
    low_max = models.PositiveIntegerField(default=30)
    mild_max = models.PositiveIntegerField(default=60)
    moderate_max = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["min_age_months", "max_age_months", "id"]

    def __str__(self):
        return f"{self.name} ({self.min_age_months}-{self.max_age_months}m)"


class AgeBandCategoryWeight(TimeStampedModel):
    """Category multiplier specific to an age scoring band."""

    age_band = models.ForeignKey(AgeScoringBand, on_delete=models.CASCADE)
    category = models.ForeignKey(QuestionCategory, on_delete=models.CASCADE)
    multiplier = models.FloatField(default=1.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["age_band", "category"],
                name="unique_age_band_category_weight",
            )
        ]

    def __str__(self):
        return f"{self.age_band.name} / {self.category.name} x{self.multiplier}"
