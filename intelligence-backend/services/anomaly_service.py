"""Rule-based anomaly detection against personal baselines.

The detector does not decide that a reading is medically abnormal. It
flags statistical deviations from an astronaut's own baseline so that a
clinician or mission controller can review them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ml.metrics import METRIC_COLUMNS
from services.comparison_service import (
    STATUS_EVALUATED,
    STATUS_INSUFFICIENT_BASELINE,
    STATUS_MISSING_CURRENT,
    STATUS_NO_BASELINE,
    compare_metric,
)

SEVERITY_NORMAL = "NORMAL"
SEVERITY_WATCH = "WATCH"
SEVERITY_ANOMALY = "ANOMALY"
SEVERITY_SEVERE = "SEVERE"
SEVERITY_NOT_EVALUATED = "NOT_EVALUATED"

SEVERITY_RANK = {
    SEVERITY_NORMAL: 0,
    SEVERITY_WATCH: 1,
    SEVERITY_ANOMALY: 2,
    SEVERITY_SEVERE: 3,
}


@dataclass(frozen=True)
class AnomalyRules:
    """Thresholds expressed in baseline standard deviations."""

    watch_z: float = 2.0
    anomaly_z: float = 3.0
    severe_z: float = 4.0
    moving_average_z: float = 2.0

    def __post_init__(self):
        if not 0 < self.watch_z < self.anomaly_z < self.severe_z:
            raise ValueError(
                "Z thresholds must satisfy 0 < watch_z < anomaly_z < severe_z"
            )
        if self.moving_average_z <= 0:
            raise ValueError("moving_average_z must be positive")


def _numeric_values(values) -> list[float]:
    if values is None:
        return []

    result = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number:
            result.append(number)
    return result


def _severity_for_z(absolute_z: float, rules: AnomalyRules) -> str:
    if absolute_z >= rules.severe_z:
        return SEVERITY_SEVERE
    if absolute_z >= rules.anomaly_z:
        return SEVERITY_ANOMALY
    if absolute_z >= rules.watch_z:
        return SEVERITY_WATCH
    return SEVERITY_NORMAL


def _max_severity(first: str, second: str) -> str:
    if SEVERITY_RANK[second] > SEVERITY_RANK[first]:
        return second
    return first


def evaluate_metric_anomaly(
    metric: str,
    current_value,
    baseline,
    *,
    recent_values=None,
    rules: AnomalyRules | None = None,
) -> dict:
    """Classify one metric using its Z-score and recent moving average."""

    rules = rules or AnomalyRules()
    comparison = compare_metric(metric, current_value, baseline)

    severity = SEVERITY_NOT_EVALUATED
    reasons = []

    recent = _numeric_values(recent_values)
    moving_average = sum(recent) / len(recent) if recent else None
    moving_average_z = None
    moving_average_severity = None

    baseline_value = comparison["baseline_value"]
    std_dev = comparison["std_dev"]

    if moving_average is not None and baseline_value is not None:
        if std_dev is not None and std_dev > 0:
            moving_average_z = (moving_average - baseline_value) / std_dev

    if comparison["status"] == STATUS_MISSING_CURRENT:
        reasons.append("The current reading has no value for this metric.")
    elif comparison["status"] == STATUS_NO_BASELINE:
        reasons.append("A personal baseline is not available for this metric.")
    elif comparison["status"] == STATUS_INSUFFICIENT_BASELINE:
        reasons.append(
            "The personal baseline has insufficient data for a reliable "
            "anomaly decision."
        )
    elif comparison["status"] != STATUS_EVALUATED:
        reasons.append("The metric could not be evaluated.")
    elif comparison["absolute_z"] is None:
        reasons.append(
            "The baseline standard deviation is unavailable or zero."
        )
    else:
        severity = _severity_for_z(
            comparison["absolute_z"],
            rules,
        )

    if (
        moving_average_z is not None
        and severity != SEVERITY_NOT_EVALUATED
    ):
        if abs(moving_average_z) >= rules.severe_z:
            moving_average_severity = SEVERITY_SEVERE
        elif abs(moving_average_z) >= rules.anomaly_z:
            moving_average_severity = SEVERITY_ANOMALY
        elif abs(moving_average_z) >= rules.moving_average_z:
            moving_average_severity = SEVERITY_WATCH

        if moving_average_severity is not None:
            severity = _max_severity(
                severity,
                moving_average_severity,
            )
            if moving_average_severity != SEVERITY_NORMAL:
                reasons.append(
                    "The recent moving average is "
                    f"{moving_average_z:+.2f} standard deviations from the "
                    "baseline."
                )

    if severity == SEVERITY_NORMAL:
        reasons.append("The value is within the configured baseline range.")

    return {
        "metric": metric,
        "metric_label": comparison["metric_label"],
        "unit": comparison["unit"],
        "severity": severity,
        "evaluated": severity != SEVERITY_NOT_EVALUATED,
        "requires_review": severity in {
            SEVERITY_WATCH,
            SEVERITY_ANOMALY,
            SEVERITY_SEVERE,
        },
        "reason": " ".join(reasons),
        "current_value": comparison["current_value"],
        "baseline_value": baseline_value,
        "std_dev": std_dev,
        "z_score": comparison["z_score"],
        "absolute_z": comparison["absolute_z"],
        "direction": comparison["direction"],
        "difference": comparison["difference"],
        "outside_observed_range": comparison[
            "outside_observed_range"
        ],
        "moving_average": moving_average,
        "moving_average_z": moving_average_z,
        "moving_average_sample_count": len(recent),
        "moving_average_severity": moving_average_severity,
        "baseline_status": comparison["baseline_status"],
        "baseline_version": comparison["baseline_version"],
        "rules": {
            "watch_z": rules.watch_z,
            "anomaly_z": rules.anomaly_z,
            "severe_z": rules.severe_z,
            "moving_average_z": rules.moving_average_z,
        },
    }


def _baseline_map(baselines) -> dict:
    if baselines is None:
        return {}
    if isinstance(baselines, Mapping):
        return {
            (key or getattr(value, "metric", None)): value
            for key, value in baselines.items()
            if key or getattr(value, "metric", None)
        }
    return {
        getattr(baseline, "metric", None): baseline
        for baseline in baselines
        if getattr(baseline, "metric", None)
    }


def _get_metric_value(reading, metric):
    if isinstance(reading, Mapping):
        return reading.get(metric)
    return getattr(reading, metric, None)


def evaluate_reading_anomalies(
    current_reading,
    baselines,
    *,
    recent_values_by_metric: Mapping | None = None,
    rules: AnomalyRules | None = None,
) -> list[dict]:
    """Evaluate every metric in a reading."""

    rules = rules or AnomalyRules()
    baseline_map = _baseline_map(baselines)
    recent_values_by_metric = recent_values_by_metric or {}

    return [
        evaluate_metric_anomaly(
            metric,
            _get_metric_value(current_reading, metric),
            baseline_map.get(metric),
            recent_values=recent_values_by_metric.get(metric),
            rules=rules,
        )
        for metric in METRIC_COLUMNS
    ]


def summarize_anomalies(anomalies: list[dict]) -> dict:
    counts = {severity: 0 for severity in SEVERITY_RANK}
    counts[SEVERITY_NOT_EVALUATED] = 0
    alerts = []
    highest = SEVERITY_NOT_EVALUATED

    for anomaly in anomalies:
        severity = anomaly["severity"]
        counts[severity] += 1

        if anomaly["requires_review"]:
            alerts.append({
                "metric": anomaly["metric"],
                "severity": severity,
                "z_score": anomaly["z_score"],
            })

        if severity == SEVERITY_NOT_EVALUATED:
            continue
        if highest == SEVERITY_NOT_EVALUATED or (
            SEVERITY_RANK[severity] > SEVERITY_RANK[highest]
        ):
            highest = severity

    return {
        "highest_severity": highest,
        "counts": counts,
        "alert_count": len(alerts),
        "alerts": alerts,
        "evaluated": counts[SEVERITY_NORMAL] + len(alerts),
    }
