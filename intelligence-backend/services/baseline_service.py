"""Personal baseline calculations.

Baselines are computed per astronaut and per metric. The service keeps
descriptive statistics (mean, median, standard deviation, minimum,
maximum and a calendar-day rolling average) and classifies how much
confidence can be placed in each baseline based on the number of
observations.

A baseline can be computed from a recent trailing window or from all
available history. An exclusive ``before`` boundary allows callers to
build a baseline as of a point in time, so a reading is never compared
against a baseline that already includes that reading.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from ml.metrics import METRIC_COLUMNS
from ml.preprocessing import coerce_types, validate_columns
from services.constants import (
    BASELINE_KIND_LONG_TERM,
    BASELINE_KIND_RECENT,
    DEFAULT_ROLLING_WINDOW_DAYS,
    MIN_SAMPLES_ESTABLISHED,
    MIN_SAMPLES_INSUFFICIENT,
    STATUS_ESTABLISHED,
    STATUS_INSUFFICIENT,
    STATUS_PROVISIONAL,
)


def classify_baseline_status(sample_count: int) -> str:
    if sample_count < MIN_SAMPLES_INSUFFICIENT:
        return STATUS_INSUFFICIENT
    if sample_count < MIN_SAMPLES_ESTABLISHED:
        return STATUS_PROVISIONAL
    return STATUS_ESTABLISHED


def baseline_kind_for_window(window_days: int | None) -> str:
    if window_days is None:
        return BASELINE_KIND_LONG_TERM
    return BASELINE_KIND_RECENT


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(number):
        return None
    return number


def _empty_statistics() -> dict:
    return {
        "baseline_value": None,
        "median_value": None,
        "std_dev": None,
        "min_value": None,
        "max_value": None,
        "rolling_average": None,
        "rolling_sample_count": 0,
        "sample_count": 0,
        "sample_start": None,
        "sample_end": None,
    }


def _metric_statistics(
    valid: pd.DataFrame,
    metric: str,
    rolling_window_days: int,
) -> dict:
    if valid.empty:
        return _empty_statistics()

    values = valid[metric]
    last_time = valid["recorded_at"].max()
    rolling_cutoff = last_time - timedelta(days=rolling_window_days)

    indexed = valid.set_index("recorded_at")[metric].sort_index()
    rolling = indexed.rolling(
        f"{rolling_window_days}D",
        min_periods=1,
    ).mean()

    return {
        "baseline_value": _optional_float(values.mean()),
        "median_value": _optional_float(values.median()),
        "std_dev": _optional_float(values.std(ddof=1)),
        "min_value": _optional_float(values.min()),
        "max_value": _optional_float(values.max()),
        "rolling_average": _optional_float(rolling.iloc[-1]),
        "rolling_sample_count": int(
            (indexed.index > rolling_cutoff).sum()
        ),
        "sample_count": int(len(valid)),
        "sample_start": valid["recorded_at"].min(),
        "sample_end": last_time,
    }


def _apply_boundaries(
    frame: pd.DataFrame,
    *,
    window_days: int | None,
    before,
) -> tuple[pd.DataFrame, object, object]:
    if frame.empty:
        return frame, None, before

    frame = frame.sort_values("recorded_at", kind="stable")

    if before is not None:
        frame = frame.loc[frame["recorded_at"] < before]

    if frame.empty:
        return frame, None, before

    data_end = frame["recorded_at"].max()

    if window_days is not None:
        if window_days < 1:
            raise ValueError("window_days must be at least 1")
        cutoff = data_end - timedelta(days=window_days)
        frame = frame.loc[frame["recorded_at"] > cutoff]

    return frame, data_end, before


def calculate_baselines(
    frame: pd.DataFrame,
    astronaut_id: str,
    *,
    window_days: int | None,
    rolling_window_days: int = DEFAULT_ROLLING_WINDOW_DAYS,
    before=None,
) -> list[dict]:
    """Calculate one baseline record per metric for an astronaut."""

    if window_days is not None and window_days < 1:
        raise ValueError("window_days must be at least 1")
    if rolling_window_days < 1:
        raise ValueError("rolling_window_days must be at least 1")

    validate_columns(frame)

    work = coerce_types(frame)
    work = work.loc[work["astronaut_id"] == str(astronaut_id)]
    work, data_end, before = _apply_boundaries(
        work,
        window_days=window_days,
        before=before,
    )

    data_start = work["recorded_at"].min() if len(work) else None
    readings_considered = int(len(work))
    baseline_kind = baseline_kind_for_window(window_days)

    records = []

    for metric in METRIC_COLUMNS:
        if len(work):
            valid = work[["recorded_at", metric]].dropna()
        else:
            valid = pd.DataFrame({
                "recorded_at": pd.Series(dtype="datetime64[ns, UTC]"),
                metric: pd.Series(dtype=float),
            })

        statistics = _metric_statistics(
            valid, metric, rolling_window_days
        )

        statistics.update({
            "astronaut_id": str(astronaut_id),
            "metric": metric,
            "rolling_window_days": int(rolling_window_days),
            "window_days": window_days,
            "baseline_kind": baseline_kind,
            "before": before,
            "data_start": data_start,
            "data_end": data_end,
            "readings_considered": readings_considered,
            "baseline_status": classify_baseline_status(
                statistics["sample_count"]
            ),
        })
        records.append(statistics)

    return records


def rolling_average_series(
    frame: pd.DataFrame,
    astronaut_id: str,
    metric: str,
    *,
    window_days: int = DEFAULT_ROLLING_WINDOW_DAYS,
) -> pd.DataFrame:
    """Return a calendar-day rolling average series for charting."""

    if metric not in METRIC_COLUMNS:
        raise ValueError(f"Unknown metric: {metric}")
    if window_days < 1:
        raise ValueError("window_days must be at least 1")

    work = coerce_types(frame)
    work = work.loc[work["astronaut_id"] == str(astronaut_id)]
    work = work.sort_values("recorded_at", kind="stable")

    valid = work[["recorded_at", metric]].dropna()

    if valid.empty:
        return pd.DataFrame(columns=[
            "recorded_at",
            metric,
            f"{metric}_rolling_average",
        ])

    indexed = valid.set_index("recorded_at")[metric].sort_index()
    rolling = indexed.rolling(
        f"{window_days}D",
        min_periods=1,
    ).mean()

    result = pd.DataFrame({
        "recorded_at": rolling.index,
        metric: indexed.to_numpy(),
        f"{metric}_rolling_average": rolling.to_numpy(),
    })

    return result.reset_index(drop=True)
