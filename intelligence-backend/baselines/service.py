"""Persistence layer for personal health baselines."""

from __future__ import annotations

import time

import pandas as pd
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Max
from django.utils import timezone

from baselines.models import BaselineSnapshot, HealthBaseline, HealthReading
from ml.metrics import METRIC_COLUMNS, READING_COLUMNS
from ml.preprocessing import sort_readings
from services.baseline_service import calculate_baselines
from services.constants import (
    DEFAULT_RECENT_WINDOW_DAYS,
    DEFAULT_ROLLING_WINDOW_DAYS,
    STATUS_INSUFFICIENT,
)

VERSION_RETRY_ATTEMPTS = 3
VERSION_RETRY_DELAY_SECONDS = 0.05


def load_readings(
    astronaut_id: str,
    *,
    before=None,
) -> pd.DataFrame:
    queryset = HealthReading.objects.filter(astronaut_id=str(astronaut_id))

    if before is not None:
        queryset = queryset.filter(recorded_at__lt=before)

    records = list(queryset.values(
        "astronaut_id", "recorded_at", *METRIC_COLUMNS
    ))

    if not records:
        return pd.DataFrame(columns=READING_COLUMNS)

    return sort_readings(pd.DataFrame.from_records(records))


def _status_summary(records: list[dict]) -> dict:
    summary = {}
    for record in records:
        status = record["baseline_status"]
        summary[status] = summary.get(status, 0) + 1
    return summary


def recalculate_baselines(
    astronaut_id: str,
    *,
    window_days: int | None = DEFAULT_RECENT_WINDOW_DAYS,
    rolling_window_days: int = DEFAULT_ROLLING_WINDOW_DAYS,
    before=None,
    calculation_date=None,
    frame: pd.DataFrame | None = None,
) -> list[HealthBaseline]:
    """Create a new baseline snapshot and version for every metric."""

    calculation_date = calculation_date or timezone.now()

    if frame is None:
        frame = load_readings(astronaut_id, before=before)

    computed = calculate_baselines(
        frame,
        astronaut_id,
        window_days=window_days,
        rolling_window_days=rolling_window_days,
        before=before,
    )

    status_summary = _status_summary(computed)
    reference = computed[0]
    reading_count = reference["readings_considered"]
    data_start = reference["data_start"]
    data_end = reference["data_end"]
    baseline_kind = reference["baseline_kind"]
    before_boundary = reference["before"]

    for attempt in range(VERSION_RETRY_ATTEMPTS):
        try:
            with transaction.atomic():
                latest_version = (
                    HealthBaseline.objects
                    .filter(astronaut_id=str(astronaut_id))
                    .aggregate(latest=Max("baseline_version"))
                    .get("latest") or 0
                )
                next_version = latest_version + 1

                snapshot = BaselineSnapshot.objects.create(
                    astronaut_id=str(astronaut_id),
                    version=next_version,
                    baseline_kind=baseline_kind,
                    window_days=window_days,
                    rolling_window_days=rolling_window_days,
                    before=before_boundary,
                    data_start=data_start,
                    data_end=data_end,
                    reading_count=reading_count,
                    metric_count=len(computed),
                    status_summary=status_summary,
                    calculation_date=calculation_date,
                )

                HealthBaseline.objects.filter(
                    astronaut_id=str(astronaut_id),
                    is_current=True,
                ).update(is_current=False)

                baselines = [
                    HealthBaseline(
                        snapshot=snapshot,
                        astronaut_id=record["astronaut_id"],
                        metric=record["metric"],
                        baseline_value=record["baseline_value"],
                        median_value=record["median_value"],
                        std_dev=record["std_dev"],
                        min_value=record["min_value"],
                        max_value=record["max_value"],
                        rolling_average=record["rolling_average"],
                        rolling_window_days=record["rolling_window_days"],
                        rolling_sample_count=record[
                            "rolling_sample_count"
                        ],
                        sample_count=record["sample_count"],
                        window_days=record["window_days"],
                        baseline_kind=record["baseline_kind"],
                        baseline_status=record["baseline_status"],
                        baseline_version=next_version,
                        is_current=True,
                        sample_start=record["sample_start"],
                        sample_end=record["sample_end"],
                        calculation_date=calculation_date,
                    )
                    for record in computed
                ]

                HealthBaseline.objects.bulk_create(baselines)

            return baselines
        except (IntegrityError, OperationalError) as error:
            locked = (
                isinstance(error, OperationalError)
                and "locked" in str(error).lower()
            )
            if isinstance(error, OperationalError) and not locked:
                raise
            if attempt == VERSION_RETRY_ATTEMPTS - 1:
                raise
            if locked:
                time.sleep(
                    VERSION_RETRY_DELAY_SECONDS * (attempt + 1)
                )

    raise RuntimeError("Baseline version allocation failed")


def store_registration_reading(
    astronaut_id: str,
    metrics: dict,
    *,
    recorded_at=None,
) -> tuple[HealthReading, bool]:
    """Store registration health data as an idempotent initial reading.

    Registration payloads do not carry a measurement time. The first
    intake therefore uses the registration moment, and later retries
    reuse that timestamp so the same astronaut is not duplicated.
    """

    if recorded_at is None:
        existing = (
            HealthReading.objects
            .filter(
                astronaut_id=str(astronaut_id),
                source="registration",
            )
            .order_by("recorded_at", "id")
            .first()
        )
        recorded_at = (
            existing.recorded_at if existing is not None else timezone.now()
        )

    defaults = {
        metric: metrics[metric]
        for metric in METRIC_COLUMNS
        if metric in metrics
    }
    defaults["source"] = "registration"

    return HealthReading.objects.update_or_create(
        astronaut_id=str(astronaut_id),
        recorded_at=recorded_at,
        defaults=defaults,
    )


def get_current_baselines(
    astronaut_id: str,
    *,
    metric: str | None = None,
    kind: str | None = None,
):
    queryset = HealthBaseline.objects.filter(
        astronaut_id=str(astronaut_id),
        is_current=True,
    ).select_related("snapshot")

    if metric is not None:
        queryset = queryset.filter(metric=metric)

    if kind is not None:
        queryset = queryset.filter(baseline_kind=kind)

    return queryset.order_by("metric")


def get_usable_baselines(astronaut_id: str, **filters):
    return get_current_baselines(astronaut_id, **filters).exclude(
        baseline_status=STATUS_INSUFFICIENT
    )


def get_current_snapshot(astronaut_id: str):
    baseline = (
        HealthBaseline.objects
        .filter(astronaut_id=str(astronaut_id), is_current=True)
        .select_related("snapshot")
        .first()
    )
    return baseline.snapshot if baseline else None


def get_baseline_history(
    astronaut_id: str,
    *,
    metric: str | None = None,
    kind: str | None = None,
    window_days: int | None = None,
    filter_window: bool = False,
    limit: int | None = None,
):
    queryset = (
        HealthBaseline.objects
        .filter(astronaut_id=str(astronaut_id))
        .select_related("snapshot")
    )

    if metric is not None:
        queryset = queryset.filter(metric=metric)

    if kind is not None:
        queryset = queryset.filter(baseline_kind=kind)

    if filter_window:
        if window_days is None:
            queryset = queryset.filter(window_days__isnull=True)
        else:
            queryset = queryset.filter(window_days=window_days)

    queryset = queryset.order_by("-baseline_version", "metric")

    if limit is not None:
        versions = list(
            BaselineSnapshot.objects
            .filter(astronaut_id=str(astronaut_id))
            .order_by("-version")
            .values_list("version", flat=True)[:limit]
        )
        queryset = queryset.filter(baseline_version__in=versions)

    return queryset


def get_current_versions(astronaut_id: str) -> dict[str, int]:
    return {
        baseline.metric: baseline.baseline_version
        for baseline in get_current_baselines(astronaut_id)
    }


def get_snapshot_history(astronaut_id: str, *, limit: int = 20):
    return BaselineSnapshot.objects.filter(
        astronaut_id=str(astronaut_id)
    ).order_by("-version")[:limit]
