from django.contrib import admin

from .models import BaselineSnapshot, HealthBaseline, HealthReading


@admin.register(HealthReading)
class HealthReadingAdmin(admin.ModelAdmin):
    list_display = (
        "astronaut_id",
        "recorded_at",
        "heart_rate",
        "oxygen_saturation",
        "sleep_duration",
        "fatigue_level",
        "source",
    )
    list_filter = ("astronaut_id", "source")
    date_hierarchy = "recorded_at"


@admin.register(BaselineSnapshot)
class BaselineSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "astronaut_id",
        "version",
        "baseline_kind",
        "window_days",
        "reading_count",
        "metric_count",
        "calculation_date",
    )
    list_filter = ("baseline_kind", "astronaut_id")
    search_fields = ("astronaut_id",)


@admin.register(HealthBaseline)
class HealthBaselineAdmin(admin.ModelAdmin):
    list_display = (
        "astronaut_id",
        "metric",
        "baseline_value",
        "std_dev",
        "sample_count",
        "baseline_status",
        "baseline_version",
        "is_current",
        "calculation_date",
    )
    list_filter = (
        "metric",
        "baseline_status",
        "is_current",
        "astronaut_id",
    )
    search_fields = ("astronaut_id",)
