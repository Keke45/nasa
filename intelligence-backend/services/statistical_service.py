"""Database-backed orchestration for statistical health intelligence."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from baselines.models import HealthReading
from baselines.service import get_current_baselines
from ml.anomaly_model import (
    STATUS_ERROR,
    STATUS_NOT_TRAINED,
    evaluate_personal_anomaly,
)
from ml.metrics import METRIC_COLUMNS
from ml.trend_prediction import (
    DEFAULT_LONG_WINDOW_DAYS,
    DEFAULT_SHORT_WINDOW_DAYS,
    TREND_INSUFFICIENT,
    TREND_STABLE,
    predict_trend,
)
from services.anomaly_service import (
    AnomalyRules,
    evaluate_reading_anomalies,
    summarize_anomalies,
)
from services.comparison_service import (
    compare_reading,
    summarize_comparisons,
)
from services.constants import (
    BASELINE_KIND_CHOICES,
    BASELINE_KIND_RECENT,
    DEFAULT_ANALYSIS_LOOKBACK_DAYS,
    DEFAULT_ROLLING_WINDOW_DAYS,
    STATUS_INSUFFICIENT,
)

DEFAULT_LOOKBACK_DAYS = DEFAULT_ANALYSIS_LOOKBACK_DAYS
ML_STATUS_DISABLED = "DISABLED"


def _validate_kind(baseline_kind: str) -> str:
    kind = str(baseline_kind).upper()
    allowed = {choice[0] for choice in BASELINE_KIND_CHOICES}
    if kind not in allowed:
        raise ValueError(
            f"baseline_kind must be one of: {', '.join(sorted(allowed))}"
        )
    return kind


def get_reading_for_analysis(
    astronaut_id: str,
    *,
    reading=None,
    reading_id: int | None = None,
    as_of=None,
) -> HealthReading:
    if reading is not None and reading_id is not None:
        raise ValueError("Provide either reading or reading_id, not both")

    if reading is not None:
        if str(reading.astronaut_id) != str(astronaut_id):
            raise ValueError("Reading does not belong to this astronaut")
        return reading

    queryset = HealthReading.objects.filter(astronaut_id=str(astronaut_id))

    if reading_id is not None:
        try:
            return queryset.get(pk=reading_id)
        except HealthReading.DoesNotExist as exc:
            raise HealthReading.DoesNotExist(
                f"Reading {reading_id} was not found for {astronaut_id}"
            ) from exc

    if as_of is not None:
        queryset = queryset.filter(recorded_at__lte=as_of)

    found = queryset.order_by("-recorded_at", "-id").first()
    if found is None:
        raise HealthReading.DoesNotExist(
            f"No readings are available for {astronaut_id}"
        )
    return found


def _load_window(
    astronaut_id: str,
    *,
    end,
    lookback_days: int,
) -> list[dict]:
    start = end - timedelta(days=lookback_days)
    return list(
        HealthReading.objects
        .filter(
            astronaut_id=str(astronaut_id),
            recorded_at__gte=start,
            recorded_at__lte=end,
        )
        .order_by("recorded_at", "id")
        .values("recorded_at", *METRIC_COLUMNS)
    )


def _recent_values(
    rows: list[dict],
    latest,
    metric: str,
    window_days: int,
) -> list[float]:
    cutoff = latest - timedelta(days=window_days)
    return [
        float(row[metric])
        for row in rows
        if row["recorded_at"] >= cutoff and row[metric] is not None
    ]


def _reading_payload(reading: HealthReading) -> dict:
    return {
        "id": reading.id,
        "recorded_at": reading.recorded_at.isoformat(),
        "source": reading.source,
        "values": {
            metric: getattr(reading, metric)
            for metric in METRIC_COLUMNS
        },
    }


def _baseline_payload(baselines, snapshot) -> dict:
    return {
        "kind": (
            snapshot.baseline_kind
            if snapshot is not None
            else None
        ),
        "snapshot_id": snapshot.id if snapshot is not None else None,
        "version": snapshot.version if snapshot is not None else None,
        "window_days": (
            snapshot.window_days if snapshot is not None else None
        ),
        "data_start": (
            snapshot.data_start.isoformat()
            if snapshot is not None and snapshot.data_start
            else None
        ),
        "data_end": (
            snapshot.data_end.isoformat()
            if snapshot is not None and snapshot.data_end
            else None
        ),
        "reading_count": (
            snapshot.reading_count if snapshot is not None else 0
        ),
        "metric_count": len(baselines),
        "usable_count": sum(
            1 for baseline in baselines if baseline.is_usable
        ),
    }


def _warnings(
    reading,
    baselines,
    snapshot,
    trends,
    ml_anomaly,
) -> list[str]:
    messages = []

    if reading.source == "simulated":
        messages.append(
            "This analysis uses simulated data and is not for clinical use."
        )

    if not baselines:
        messages.append(
            "No current baselines match the requested kind. Recalculate "
            "baselines before interpreting comparisons."
        )
    else:
        missing = set(METRIC_COLUMNS) - {
            baseline.metric for baseline in baselines
        }
        if missing:
            messages.append(
                "No baseline for: " + ", ".join(sorted(missing)) + "."
            )

        insufficient = [
            baseline.metric
            for baseline in baselines
            if baseline.baseline_status == STATUS_INSUFFICIENT
        ]
        if insufficient:
            messages.append(
                "Insufficient baseline data for: "
                + ", ".join(sorted(insufficient))
                + "."
            )

    if snapshot is not None and snapshot.data_end is not None:
        if snapshot.data_end >= reading.recorded_at:
            messages.append(
                "The baseline snapshot extends to or beyond the analysed "
                "reading, so the comparison is not strictly as-of clean."
            )

    weak_trends = [
        metric
        for metric, trend in trends.items()
        if trend["direction"] == TREND_STABLE and not trend["reliable"]
    ]
    insufficient_trends = [
        metric
        for metric, trend in trends.items()
        if trend["direction"] == TREND_INSUFFICIENT
    ]
    if insufficient_trends:
        messages.append(
            "Not enough history for a trend in: "
            + ", ".join(sorted(insufficient_trends))
            + "."
        )
    elif weak_trends:
        messages.append(
            "Weak trend fits for: " + ", ".join(sorted(weak_trends)) + "."
        )

    if ml_anomaly["status"] == STATUS_NOT_TRAINED:
        messages.append(
            "No personal ML anomaly model has been trained for this "
            "astronaut."
        )
    elif ml_anomaly["status"] == STATUS_ERROR:
        messages.append(
            "The personal ML anomaly model could not be evaluated: "
            + ml_anomaly.get("error", "unknown error")
        )
    elif ml_anomaly.get("in_sample"):
        messages.append(
            "The ML anomaly model was trained through this reading, so "
            "its score is in-sample."
        )

    return messages


def analyze_statistics(
    astronaut_id: str,
    *,
    reading=None,
    reading_id: int | None = None,
    as_of=None,
    baseline_kind: str = BASELINE_KIND_RECENT,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    rolling_window_days: int = DEFAULT_ROLLING_WINDOW_DAYS,
    short_window_days: int = DEFAULT_SHORT_WINDOW_DAYS,
    long_window_days: int = DEFAULT_LONG_WINDOW_DAYS,
    anomaly_rules: AnomalyRules | None = None,
    include_ml: bool = True,
) -> dict:
    """Build comparisons, anomalies and trends for one reading."""

    if lookback_days < 1:
        raise ValueError("lookback_days must be at least 1")
    if rolling_window_days < 1:
        raise ValueError("rolling_window_days must be at least 1")
    if short_window_days > long_window_days:
        raise ValueError(
            "short_window_days must not exceed long_window_days"
        )
    if long_window_days > lookback_days:
        raise ValueError(
            "long_window_days must not exceed lookback_days"
        )

    baseline_kind = _validate_kind(baseline_kind)
    reading = get_reading_for_analysis(
        astronaut_id,
        reading=reading,
        reading_id=reading_id,
        as_of=as_of,
    )

    baselines = list(
        get_current_baselines(astronaut_id, kind=baseline_kind)
    )
    snapshot = baselines[0].snapshot if baselines else None

    rows = _load_window(
        astronaut_id,
        end=reading.recorded_at,
        lookback_days=lookback_days,
    )

    comparisons = compare_reading(reading, baselines)
    recent_values = {
        metric: _recent_values(
            rows,
            reading.recorded_at,
            metric,
            rolling_window_days,
        )
        for metric in METRIC_COLUMNS
    }
    anomalies = evaluate_reading_anomalies(
        reading,
        baselines,
        recent_values_by_metric=recent_values,
        rules=anomaly_rules,
    )
    trends = {
        metric: predict_trend(
            rows,
            metric,
            short_window_days=short_window_days,
            long_window_days=long_window_days,
        )
        for metric in METRIC_COLUMNS
    }

    if include_ml:
        ml_anomaly = evaluate_personal_anomaly(
            astronaut_id,
            reading,
        )
    else:
        ml_anomaly = {
            "status": ML_STATUS_DISABLED,
            "evaluated": False,
            "is_anomaly": None,
            "reason": "ML anomaly scoring was not requested.",
        }

    comparison_summary = summarize_comparisons(comparisons)
    anomaly_summary = summarize_anomalies(anomalies)
    trend_counts = {}
    for trend in trends.values():
        direction = trend["direction"]
        trend_counts[direction] = trend_counts.get(direction, 0) + 1

    return {
        "astronaut_id": str(astronaut_id),
        "reading": _reading_payload(reading),
        "baseline": _baseline_payload(baselines, snapshot),
        "comparisons": comparisons,
        "anomalies": anomalies,
        "trends": trends,
        "summary": {
            "comparison": comparison_summary,
            "anomaly": anomaly_summary,
            "trend_directions": trend_counts,
            "ml_anomaly": {
                "status": ml_anomaly["status"],
                "is_anomaly": ml_anomaly.get("is_anomaly"),
                "anomaly_score": ml_anomaly.get("anomaly_score"),
            },
            "requires_review": (
                anomaly_summary["alert_count"] > 0
                or ml_anomaly.get("is_anomaly") is True
            ),
        },
        "ml_anomaly": ml_anomaly,
        "warnings": _warnings(
            reading,
            baselines,
            snapshot,
            trends,
            ml_anomaly,
        ),
        "generated_at": timezone.now().isoformat(),
    }
