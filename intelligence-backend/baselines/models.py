"""Database models for health readings and personal baselines."""

from django.db import models
from django.db.models import Q

from ml.metrics import METRIC_COLUMNS, METRIC_LABELS
from services.constants import (
    BASELINE_KIND_CHOICES,
    BASELINE_KIND_RECENT,
    STATUS_CHOICES,
    STATUS_ESTABLISHED as ESTABLISHED_STATUS,
    STATUS_INSUFFICIENT as INSUFFICIENT_STATUS,
    STATUS_PROVISIONAL as PROVISIONAL_STATUS,
)


class HealthReading(models.Model):
    astronaut_id = models.CharField(max_length=64, db_index=True)
    recorded_at = models.DateTimeField(db_index=True)
    heart_rate = models.FloatField(null=True, blank=True)
    systolic_bp = models.FloatField(null=True, blank=True)
    diastolic_bp = models.FloatField(null=True, blank=True)
    body_temperature = models.FloatField(null=True, blank=True)
    oxygen_saturation = models.FloatField(null=True, blank=True)
    sleep_duration = models.FloatField(null=True, blank=True)
    physical_activity = models.FloatField(null=True, blank=True)
    fatigue_level = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=32, default="simulated")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["astronaut_id", "recorded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["astronaut_id", "recorded_at"],
                name="unique_reading_per_astronaut_time",
            )
        ]
        indexes = [
            models.Index(fields=["astronaut_id", "recorded_at"]),
        ]

    def __str__(self):
        return f"{self.astronaut_id} @ {self.recorded_at:%Y-%m-%d %H:%M}"


class BaselineSnapshot(models.Model):
    """A versioned set of personal baselines.

    Analyses reference a snapshot so the exact baseline data used by a
    finding can always be reconstructed.
    """

    astronaut_id = models.CharField(max_length=64, db_index=True)
    version = models.PositiveIntegerField()
    baseline_kind = models.CharField(
        max_length=16,
        choices=BASELINE_KIND_CHOICES,
        default=BASELINE_KIND_RECENT,
    )
    window_days = models.PositiveIntegerField(null=True, blank=True)
    rolling_window_days = models.PositiveIntegerField(default=7)
    before = models.DateTimeField(null=True, blank=True)
    data_start = models.DateTimeField(null=True, blank=True)
    data_end = models.DateTimeField(null=True, blank=True)
    reading_count = models.PositiveIntegerField(default=0)
    metric_count = models.PositiveIntegerField(default=0)
    status_summary = models.JSONField(default=dict)
    calculation_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["astronaut_id", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["astronaut_id", "version"],
                name="unique_snapshot_astronaut_version",
            )
        ]
        indexes = [
            models.Index(
                fields=["astronaut_id", "-version"],
                name="baselines_b_astrona_9b5b77_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.astronaut_id} baseline snapshot v{self.version} "
            f"({self.baseline_kind})"
        )


class HealthBaseline(models.Model):
    STATUS_INSUFFICIENT = INSUFFICIENT_STATUS
    STATUS_PROVISIONAL = PROVISIONAL_STATUS
    STATUS_ESTABLISHED = ESTABLISHED_STATUS

    STATUS_CHOICES = STATUS_CHOICES

    METRIC_CHOICES = [
        (metric, METRIC_LABELS.get(metric, metric))
        for metric in METRIC_COLUMNS
    ]

    snapshot = models.ForeignKey(
        BaselineSnapshot,
        on_delete=models.PROTECT,
        related_name="baselines",
    )
    astronaut_id = models.CharField(max_length=64, db_index=True)
    metric = models.CharField(max_length=32, choices=METRIC_CHOICES)
    baseline_value = models.FloatField(null=True, blank=True)
    median_value = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    rolling_average = models.FloatField(null=True, blank=True)
    rolling_window_days = models.PositiveIntegerField(default=7)
    rolling_sample_count = models.PositiveIntegerField(default=0)
    sample_count = models.PositiveIntegerField(default=0)
    window_days = models.PositiveIntegerField(null=True, blank=True)
    baseline_kind = models.CharField(
        max_length=16,
        choices=BASELINE_KIND_CHOICES,
        default=BASELINE_KIND_RECENT,
    )
    baseline_status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_INSUFFICIENT,
    )
    baseline_version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    sample_start = models.DateTimeField(null=True, blank=True)
    sample_end = models.DateTimeField(null=True, blank=True)
    calculation_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["astronaut_id", "metric", "-baseline_version"]
        constraints = [
            models.UniqueConstraint(
                fields=["astronaut_id", "metric", "baseline_version"],
                name="unique_baseline_metric_version",
            ),
            models.UniqueConstraint(
                fields=["astronaut_id", "metric"],
                condition=Q(is_current=True),
                name="unique_current_baseline_per_metric",
            ),
        ]
        indexes = [
            models.Index(fields=["astronaut_id", "metric", "is_current"]),
            models.Index(
                fields=["astronaut_id", "baseline_kind", "is_current"],
                name="baselines_kind_current_idx",
            ),
        ]

    @property
    def is_usable(self) -> bool:
        return self.baseline_status != self.STATUS_INSUFFICIENT

    def __str__(self):
        return (
            f"{self.astronaut_id} {self.metric} "
            f"v{self.baseline_version} ({self.baseline_status})"
        )
