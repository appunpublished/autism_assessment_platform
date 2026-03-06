from django.db import migrations


def seed_age_bands(apps, schema_editor):
    AgeScoringBand = apps.get_model("assessment", "AgeScoringBand")
    QuestionCategory = apps.get_model("assessment", "QuestionCategory")
    AgeBandCategoryWeight = apps.get_model("assessment", "AgeBandCategoryWeight")

    bands = [
        ("Early Childhood", 12, 59, 24, 45, 70),
        ("School Age", 60, 143, 30, 60, 95),
        ("Adolescent", 144, 216, 36, 68, 105),
    ]

    created_bands = {}
    for name, min_m, max_m, low, mild, moderate in bands:
        band, _ = AgeScoringBand.objects.get_or_create(
            name=name,
            defaults={
                "min_age_months": min_m,
                "max_age_months": max_m,
                "low_max": low,
                "mild_max": mild,
                "moderate_max": moderate,
            },
        )
        created_bands[name] = band

    multipliers = {
        "Early Childhood": {
            "Social Communication": 1.20,
            "Repetitive Behaviour": 1.15,
            "Sensory Sensitivity": 1.10,
            "Development": 1.35,
        },
        "School Age": {
            "Social Communication": 1.05,
            "Repetitive Behaviour": 1.00,
            "Sensory Sensitivity": 1.00,
            "Development": 1.00,
        },
        "Adolescent": {
            "Social Communication": 1.20,
            "Repetitive Behaviour": 1.10,
            "Sensory Sensitivity": 0.95,
            "Development": 0.75,
        },
    }

    for category in QuestionCategory.objects.all():
        for band_name, category_map in multipliers.items():
            multiplier = category_map.get(category.name, 1.0)
            AgeBandCategoryWeight.objects.get_or_create(
                age_band=created_bands[band_name],
                category=category,
                defaults={"multiplier": multiplier},
            )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0003_agescoringband_assessmentdraft_agebandcategoryweight'),
    ]

    operations = [
        migrations.RunPython(seed_age_bands, noop_reverse),
    ]
