"""Serializers for health readings, baselines and snapshots."""

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from baselines.models import BaselineSnapshot, HealthBaseline, HealthReading
from ml.metrics import METRIC_COLUMNS, METRIC_RANGES, METRIC_UNITS
from ml.trend_prediction import (
    DEFAULT_LONG_WINDOW_DAYS,
    DEFAULT_SHORT_WINDOW_DAYS,
)
from services.anomaly_service import AnomalyRules
from services.constants import (
    BASELINE_KIND_CHOICES,
    BASELINE_KIND_RECENT,
    DEFAULT_ANALYSIS_LOOKBACK_DAYS,
    DEFAULT_RECENT_WINDOW_DAYS,
    DEFAULT_ROLLING_WINDOW_DAYS,
)


class HealthBaselineSerializer(serializers.ModelSerializer):
    metric_label = serializers.CharField(
        source="get_metric_display", read_only=True
    )
    unit = serializers.SerializerMethodField()
    is_usable = serializers.BooleanField(read_only=True)
    snapshot_id = serializers.IntegerField(
        source="snapshot.id", read_only=True
    )

    class Meta:
        model = HealthBaseline
        fields = [
            "id",
            "snapshot_id",
            "astronaut_id",
            "metric",
            "metric_label",
            "unit",
            "baseline_value",
            "median_value",
            "std_dev",
            "min_value",
            "max_value",
            "rolling_average",
            "rolling_window_days",
            "rolling_sample_count",
            "sample_count",
            "window_days",
            "baseline_kind",
            "baseline_status",
            "is_usable",
            "baseline_version",
            "is_current",
            "sample_start",
            "sample_end",
            "calculation_date",
        ]

    def get_unit(self, obj):
        return METRIC_UNITS.get(obj.metric)


class BaselineSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineSnapshot
        fields = [
            "id",
            "astronaut_id",
            "version",
            "baseline_kind",
            "window_days",
            "rolling_window_days",
            "before",
            "data_start",
            "data_end",
            "reading_count",
            "metric_count",
            "status_summary",
            "calculation_date",
            "created_at",
        ]


REGISTRATION_METRIC_MAP = {
    "resting_heart_rate": "heart_rate",
    "systolic_bp": "systolic_bp",
    "diastolic_bp": "diastolic_bp",
    "oxygen_saturation": "oxygen_saturation",
    "body_temperature": "body_temperature",
}


class RegistrationPersonalSerializer(serializers.Serializer):
    astronaut_id = serializers.CharField(
        max_length=64,
        trim_whitespace=True,
    )

    def validate_astronaut_id(self, value):
        if not value:
            raise serializers.ValidationError("astronaut_id is required")
        return value


class RegistrationHealthSerializer(serializers.Serializer):
    resting_heart_rate = serializers.FloatField(required=False)
    systolic_bp = serializers.FloatField(required=False)
    diastolic_bp = serializers.FloatField(required=False)
    oxygen_saturation = serializers.FloatField(required=False)
    body_temperature = serializers.FloatField(required=False)

    def validate(self, attrs):
        mapped = {}

        for source_field, metric in REGISTRATION_METRIC_MAP.items():
            value = attrs.get(source_field)
            if value is None:
                continue

            low, high = METRIC_RANGES[metric]
            if not (low <= value <= high):
                raise serializers.ValidationError({
                    source_field: (
                        f"value must be between {low} and {high}"
                    )
                })
            mapped[metric] = float(value)

        if not mapped:
            raise serializers.ValidationError(
                "at least one health metric is required"
            )

        systolic = attrs.get("systolic_bp")
        diastolic = attrs.get("diastolic_bp")
        if (
            systolic is not None
            and diastolic is not None
            and systolic <= diastolic
        ):
            raise serializers.ValidationError(
                "systolic_bp must be greater than diastolic_bp"
            )

        attrs["mapped_metrics"] = mapped
        return attrs


class RegistrationIntakeSerializer(serializers.Serializer):
    personal = RegistrationPersonalSerializer()
    health = RegistrationHealthSerializer()
    recorded_at = serializers.DateTimeField(required=False)

    def validate_recorded_at(self, value):
        if value > timezone.now() + timedelta(days=1):
            raise serializers.ValidationError(
                "recorded_at cannot be more than one day in the future"
            )
        return value


class HealthReadingSerializer(serializers.ModelSerializer):
    source = serializers.CharField(
        max_length=32, required=False, default="external"
    )

    class Meta:
        model = HealthReading
        fields = [
            "id",
            "astronaut_id",
            "recorded_at",
            "heart_rate",
            "systolic_bp",
            "diastolic_bp",
            "body_temperature",
            "oxygen_saturation",
            "sleep_duration",
            "physical_activity",
            "fatigue_level",
            "source",
        ]
        read_only_fields = ["id"]
        validators = []

    def validate_astronaut_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("astronaut_id is required")
        return value

    def validate_recorded_at(self, value):
        if value > timezone.now() + timedelta(days=1):
            raise serializers.ValidationError(
                "recorded_at cannot be more than one day in the future"
            )
        return value

    def validate(self, attrs):
        present = False

        for metric in METRIC_COLUMNS:
            value = attrs.get(metric)
            if value is None:
                continue

            present = True
            low, high = METRIC_RANGES[metric]
            if not (low <= value <= high):
                raise serializers.ValidationError({
                    metric: (
                        f"value must be between {low} and {high}"
                    )
                })

        if not present:
            raise serializers.ValidationError(
                "at least one health metric is required"
            )

        systolic = attrs.get("systolic_bp")
        diastolic = attrs.get("diastolic_bp")
        if (
            systolic is not None
            and diastolic is not None
            and systolic <= diastolic
        ):
            raise serializers.ValidationError(
                "systolic_bp must be greater than diastolic_bp"
            )

        return attrs


class CalculateBaselineSerializer(serializers.Serializer):
    window_days = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        default=DEFAULT_RECENT_WINDOW_DAYS,
    )
    rolling_window_days = serializers.IntegerField(
        required=False,
        min_value=1,
        default=DEFAULT_ROLLING_WINDOW_DAYS,
    )
    before = serializers.DateTimeField(required=False, allow_null=True)


class StatisticalAnalysisQuerySerializer(serializers.Serializer):
    reading_id = serializers.IntegerField(required=False, min_value=1)
    as_of = serializers.DateTimeField(required=False)
    baseline_kind = serializers.ChoiceField(
        choices=[choice[0] for choice in BASELINE_KIND_CHOICES],
        required=False,
        default=BASELINE_KIND_RECENT,
    )
    lookback_days = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=3650,
        default=DEFAULT_ANALYSIS_LOOKBACK_DAYS,
    )
    rolling_window_days = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        default=DEFAULT_ROLLING_WINDOW_DAYS,
    )
    short_window_days = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        default=DEFAULT_SHORT_WINDOW_DAYS,
    )
    long_window_days = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=3650,
        default=DEFAULT_LONG_WINDOW_DAYS,
    )
    watch_z = serializers.FloatField(
        required=False,
        default=2.0,
    )
    anomaly_z = serializers.FloatField(
        required=False,
        default=3.0,
    )
    severe_z = serializers.FloatField(
        required=False,
        default=4.0,
    )
    moving_average_z = serializers.FloatField(
        required=False,
        default=2.0,
    )
    include_ml = serializers.BooleanField(
        required=False,
        default=True,
    )

    def validate(self, attrs):
        if attrs.get("reading_id") is not None and attrs.get("as_of"):
            raise serializers.ValidationError(
                "Use either reading_id or as_of, not both"
            )

        if attrs["short_window_days"] > attrs["long_window_days"]:
            raise serializers.ValidationError(
                "short_window_days must not exceed long_window_days"
            )

        if attrs["long_window_days"] > attrs["lookback_days"]:
            raise serializers.ValidationError(
                "long_window_days must not exceed lookback_days"
            )

        try:
            attrs["anomaly_rules"] = AnomalyRules(
                watch_z=attrs["watch_z"],
                anomaly_z=attrs["anomaly_z"],
                severe_z=attrs["severe_z"],
                moving_average_z=attrs["moving_average_z"],
            )
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error

        return attrs
