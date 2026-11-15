"""Compare current health measurements with personal baselines."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ml.metrics import (
    METRIC_COLUMNS,
    METRIC_LABELS,
    METRIC_UNITS,
)
from services.constants import STATUS_INSUFFICIENT

STATUS_EVALUATED = "EVALUATED"
STATUS_NO_BASELINE = "NO_BASELINE"
STATUS_MISSING_CURRENT = "MISSING_CURRENT"
STATUS_INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"

DIRECTION_ABOVE = "ABOVE"
DIRECTION_BELOW = "BELOW"
DIRECTION_AT = "AT_BASELINE"
DIRECTION_UNKNOWN = "UNKNOWN"

DEVIATION_WATCH_Z = 2.0


def _get(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _optional_float(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(number):
        return None
    return number


def _baseline_map(baselines) -> dict:
    if baselines is None:
        return {}

    if isinstance(baselines, Mapping):
        result = {}
        for key, value in baselines.items():
            metric = key or _get(value, "metric")
            if metric:
                result[metric] = value
        return result

    result = {}
    for baseline in baselines:
        metric = _get(baseline, "metric")
        if metric:
            result[metric] = baseline
    return result


def _is_usable(baseline) -> bool:
    if baseline is None:
        return False

    explicit = _get(baseline, "is_usable")
    if explicit is not None:
        return bool(explicit)

    status = _get(baseline, "baseline_status")
    return status != STATUS_INSUFFICIENT


def compare_metric(
    metric: str,
    current_value,
    baseline,
) -> dict:
    """Compare one current value with one personal baseline."""

    current = _optional_float(current_value)
    baseline_value = _optional_float(_get(baseline, "baseline_value"))
    std_dev = _optional_float(_get(baseline, "std_dev"))
    minimum = _optional_float(_get(baseline, "min_value"))
    maximum = _optional_float(_get(baseline, "max_value"))
    median = _optional_float(_get(baseline, "median_value"))
    rolling_average = _optional_float(_get(baseline, "rolling_average"))

    usable = _is_usable(baseline)

    difference = None
    percentage_change = None
    z_score = None
    absolute_z = None
    outside_range = False
    distance_outside_range = None
    range_span = None
    range_position = None

    if current is not None and baseline_value is not None:
        difference = current - baseline_value

        if baseline_value != 0:
            percentage_change = (difference / baseline_value) * 100

        if std_dev is not None and std_dev > 0:
            z_score = difference / std_dev
            absolute_z = abs(z_score)

        if minimum is not None and maximum is not None:
            range_span = maximum - minimum
            outside_range = current < minimum or current > maximum

            if current > maximum:
                distance_outside_range = current - maximum
            elif current < minimum:
                distance_outside_range = minimum - current
            else:
                distance_outside_range = 0.0

            if range_span > 0:
                range_position = (current - minimum) / range_span

    if current is None:
        status = STATUS_MISSING_CURRENT
    elif baseline is None or baseline_value is None:
        status = STATUS_NO_BASELINE
    elif not usable:
        status = STATUS_INSUFFICIENT_BASELINE
    else:
        status = STATUS_EVALUATED

    evaluated = status == STATUS_EVALUATED

    if difference is None:
        direction = DIRECTION_UNKNOWN
    elif difference > 0:
        direction = DIRECTION_ABOVE
    elif difference < 0:
        direction = DIRECTION_BELOW
    else:
        direction = DIRECTION_AT

    label = METRIC_LABELS.get(metric, metric)
    unit = METRIC_UNITS.get(metric, "")

    if status == STATUS_MISSING_CURRENT:
        summary = f"No current {label.lower()} measurement is available."
    elif status == STATUS_NO_BASELINE:
        summary = f"No personal baseline is available for {label.lower()}."
    else:
        direction_text = {
            DIRECTION_ABOVE: "above",
            DIRECTION_BELOW: "below",
            DIRECTION_AT: "at",
            DIRECTION_UNKNOWN: "compared with",
        }[direction]
        summary = (
            f"{label} is {abs(difference):.2f} {unit} {direction_text} "
            f"the personal baseline of {baseline_value:.2f} {unit}."
        )
        if z_score is not None:
            summary += f" Z-score: {z_score:+.2f}."
        else:
            summary += " Standard deviation is unavailable, so no Z-score."
        if outside_range:
            summary += (
                f" The value is outside the observed personal range "
                f"({minimum:.2f}-{maximum:.2f} {unit})."
            )
        if not usable:
            summary += (
                " The baseline is based on insufficient data, so this "
                "comparison is not reliable."
            )

    return {
        "metric": metric,
        "metric_label": label,
        "unit": unit,
        "status": status,
        "evaluated": evaluated,
        "current_value": current,
        "baseline_value": baseline_value,
        "median_value": median,
        "std_dev": std_dev,
        "min_value": minimum,
        "max_value": maximum,
        "rolling_average": rolling_average,
        "baseline_status": _get(baseline, "baseline_status"),
        "baseline_version": _get(baseline, "baseline_version"),
        "snapshot_id": _get(baseline, "snapshot_id"),
        "baseline_kind": _get(baseline, "baseline_kind"),
        "window_days": _get(baseline, "window_days"),
        "sample_count": _get(baseline, "sample_count"),
        "difference": difference,
        "percentage_change": percentage_change,
        "z_score": z_score,
        "absolute_z": absolute_z,
        "direction": direction,
        "outside_observed_range": outside_range,
        "distance_outside_range": distance_outside_range,
        "range_span": range_span,
        "range_position": range_position,
        "summary": summary,
    }


def compare_reading(current_reading, baselines) -> list[dict]:
    """Compare every metric in a reading with the matching baselines."""

    baseline_map = _baseline_map(baselines)

    return [
        compare_metric(
            metric,
            _get(current_reading, metric),
            baseline_map.get(metric),
        )
        for metric in METRIC_COLUMNS
    ]


def summarize_comparisons(comparisons: list[dict]) -> dict:
    status_counts = {}
    outside_range = []
    strongest = None

    for comparison in comparisons:
        status = comparison["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

        if comparison["outside_observed_range"]:
            outside_range.append(comparison["metric"])

        absolute_z = comparison["absolute_z"]
        if absolute_z is not None and (
            strongest is None or absolute_z > strongest["absolute_z"]
        ):
            strongest = {
                "metric": comparison["metric"],
                "absolute_z": absolute_z,
                "z_score": comparison["z_score"],
            }

    return {
        "evaluated": status_counts.get(STATUS_EVALUATED, 0),
        "status_counts": status_counts,
        "outside_observed_range": outside_range,
        "strongest_deviation": strongest,
        "deviations_over_2sd": [
            comparison["metric"]
            for comparison in comparisons
            if comparison["absolute_z"] is not None
            and comparison["absolute_z"] >= DEVIATION_WATCH_Z
        ],
    }
