"""Time-based trend estimation for astronaut health metrics.

A trend is fitted against elapsed days rather than row numbers so that
missing readings and irregular collection intervals do not distort the
slope. Directions use a relative slope threshold to avoid labelling tiny
changes as meaningful trends.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

import numpy as np
import pandas as pd

from ml.metrics import METRIC_COLUMNS, METRIC_LABELS, METRIC_UNITS

TREND_INCREASING = "INCREASING"
TREND_DECREASING = "DECREASING"
TREND_STABLE = "STABLE"
TREND_INSUFFICIENT = "INSUFFICIENT"

DEFAULT_MIN_SAMPLES = 5
DEFAULT_SHORT_WINDOW_DAYS = 7
DEFAULT_LONG_WINDOW_DAYS = 30
DEFAULT_STABLE_RELATIVE_SLOPE = 0.005
DEFAULT_MIN_R_SQUARED = 0.3
DEFAULT_PROJECTION_DAYS = 7


def _to_utc_timestamp(value):
    if value is None:
        return None
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(stamp):
        return None
    if stamp.tzinfo is None:
        return stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC")


def _records_to_points(readings, metric: str) -> list[tuple]:
    if isinstance(readings, pd.DataFrame):
        if metric not in readings.columns:
            return []
        subset = readings[["recorded_at", metric]].dropna()
        raw = list(zip(subset["recorded_at"], subset[metric]))
    else:
        raw = []
        for reading in readings:
            if isinstance(reading, Mapping):
                timestamp = reading.get("recorded_at")
                value = reading.get(metric)
            else:
                timestamp = getattr(reading, "recorded_at", None)
                value = getattr(reading, metric, None)
            if timestamp is not None and value is not None:
                raw.append((timestamp, value))

    points = []
    for timestamp, value in raw:
        stamp = _to_utc_timestamp(timestamp)
        if stamp is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isnan(number):
            continue
        points.append((stamp, number))

    points.sort(key=lambda point: point[0])
    return points


def _moving_average(points, latest, window_days: int) -> float | None:
    cutoff = latest - timedelta(days=window_days)
    values = [value for stamp, value in points if stamp >= cutoff]
    if not values:
        return None
    return float(np.mean(values))


def _insufficient_result(metric: str, sample_count: int) -> dict:
    label = METRIC_LABELS.get(metric, metric)
    return {
        "metric": metric,
        "metric_label": label,
        "unit": METRIC_UNITS.get(metric, ""),
        "direction": TREND_INSUFFICIENT,
        "reliable": False,
        "sample_count": sample_count,
        "trend_duration_days": None,
        "slope_per_day": None,
        "slope_per_week": None,
        "relative_slope_per_day": None,
        "r_squared": None,
        "first_value": None,
        "latest_value": None,
        "short_moving_average": None,
        "long_moving_average": None,
        "projection_days": None,
        "projected_change": None,
        "projected_value": None,
        "projected_percentage_change": None,
        "summary": (
            f"Not enough {label.lower()} observations to estimate a trend."
        ),
    }


def predict_trend(
    readings,
    metric: str,
    *,
    short_window_days: int = DEFAULT_SHORT_WINDOW_DAYS,
    long_window_days: int = DEFAULT_LONG_WINDOW_DAYS,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    stable_relative_slope: float = DEFAULT_STABLE_RELATIVE_SLOPE,
    min_r_squared: float = DEFAULT_MIN_R_SQUARED,
    projection_days: int = DEFAULT_PROJECTION_DAYS,
) -> dict:
    """Estimate the linear trend of one metric over calendar time."""

    if metric not in METRIC_COLUMNS:
        raise ValueError(f"Unknown metric: {metric}")
    if short_window_days < 1 or long_window_days < 1:
        raise ValueError("Moving-average windows must be at least 1 day")
    if short_window_days > long_window_days:
        raise ValueError(
            "short_window_days must not exceed long_window_days"
        )
    if min_samples < 2:
        raise ValueError("min_samples must be at least 2")
    if stable_relative_slope < 0:
        raise ValueError("stable_relative_slope must be non-negative")
    if not 0 <= min_r_squared <= 1:
        raise ValueError("min_r_squared must be between 0 and 1")
    if projection_days < 0:
        raise ValueError("projection_days must be non-negative")

    points = _records_to_points(readings, metric)
    sample_count = len(points)

    if sample_count < min_samples:
        return _insufficient_result(metric, sample_count)

    latest = points[-1][0]
    elapsed_days = np.array([
        (stamp - points[0][0]).total_seconds() / 86400
        for stamp, _ in points
    ])
    values = np.array([value for _, value in points], dtype=float)

    if elapsed_days[-1] <= 0:
        return _insufficient_result(metric, sample_count)

    slope, intercept = np.polyfit(elapsed_days, values, 1)
    fitted = slope * elapsed_days + intercept
    residual_sum = float(np.sum((values - fitted) ** 2))
    total_sum = float(np.sum((values - values.mean()) ** 2))

    if total_sum == 0:
        r_squared = 1.0
    else:
        r_squared = max(0.0, 1.0 - residual_sum / total_sum)

    mean_value = float(values.mean())
    denominator = max(abs(mean_value), 1.0)
    relative_slope = abs(float(slope)) / denominator

    if relative_slope < stable_relative_slope:
        direction = TREND_STABLE
    elif slope > 0:
        direction = TREND_INCREASING
    else:
        direction = TREND_DECREASING

    latest_value = float(values[-1])
    projected_change = float(slope) * projection_days
    projected_value = latest_value + projected_change
    projected_percentage = None
    if latest_value != 0:
        projected_percentage = (projected_change / latest_value) * 100

    label = METRIC_LABELS.get(metric, metric)
    unit = METRIC_UNITS.get(metric, "")
    trend_duration = float(elapsed_days[-1])
    reliable = r_squared >= min_r_squared

    if direction == TREND_STABLE:
        summary = (
            f"{label} is stable over {trend_duration:.1f} days "
            f"(slope {slope:+.4f} {unit}/day, R-squared "
            f"{r_squared:.2f})."
        )
    else:
        summary = (
            f"{label} is {direction.lower()} by {abs(slope):.4f} "
            f"{unit}/day over {trend_duration:.1f} days "
            f"(R-squared {r_squared:.2f})."
        )
    summary += (
        f" Projected change over {projection_days} days: "
        f"{projected_change:+.2f} {unit}."
    )
    if not reliable:
        summary += (
            " The fit is weak, so the direction should be interpreted "
            "cautiously."
        )

    return {
        "metric": metric,
        "metric_label": label,
        "unit": unit,
        "direction": direction,
        "reliable": reliable,
        "sample_count": sample_count,
        "trend_duration_days": trend_duration,
        "slope_per_day": float(slope),
        "slope_per_week": float(slope) * 7,
        "relative_slope_per_day": relative_slope,
        "r_squared": r_squared,
        "first_value": float(values[0]),
        "latest_value": latest_value,
        "short_moving_average": _moving_average(
            points, latest, short_window_days
        ),
        "long_moving_average": _moving_average(
            points, latest, long_window_days
        ),
        "projection_days": projection_days,
        "projected_change": projected_change,
        "projected_value": projected_value,
        "projected_percentage_change": projected_percentage,
        "summary": summary,
    }


def predict_metric_trends(
    readings,
    *,
    metrics=None,
    **kwargs,
) -> dict:
    """Estimate trends for several metrics, keyed by metric name."""

    metrics = metrics or METRIC_COLUMNS
    return {
        metric: predict_trend(readings, metric, **kwargs)
        for metric in metrics
    }
