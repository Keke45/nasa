"""Data preparation for astronaut health readings.

The preprocessing layer makes raw readings safe to analyse without
discarding unusual observations. Missing values, duplicates, invalid
timestamps and out-of-range values are reported rather than silently
removed, because unusual readings may be the most important evidence
for the intelligence engine.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

from ml.metrics import METRIC_COLUMNS, METRIC_RANGES, READING_COLUMNS

SCALERS = {
    "standard": StandardScaler,
    "robust": RobustScaler,
    "minmax": MinMaxScaler,
}


def validate_columns(
    frame: pd.DataFrame,
    required: Iterable[str] = READING_COLUMNS,
) -> pd.DataFrame:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return frame


def coerce_types(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    if "astronaut_id" in result.columns:
        result["astronaut_id"] = (
            result["astronaut_id"].astype("string").str.strip()
        )

    if "recorded_at" in result.columns:
        result["recorded_at"] = pd.to_datetime(
            result["recorded_at"], utc=True, errors="coerce"
        )

    for metric in METRIC_COLUMNS:
        if metric in result.columns:
            result[metric] = pd.to_numeric(result[metric], errors="coerce")

    return result


def remove_duplicates(
    frame: pd.DataFrame,
    *,
    subset: tuple[str, ...] = ("astronaut_id", "recorded_at"),
    keep: str = "last",
) -> pd.DataFrame:
    return frame.drop_duplicates(subset=list(subset), keep=keep)


def sort_readings(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        ["astronaut_id", "recorded_at"], kind="stable"
    ).reset_index(drop=True)


def missing_report(frame: pd.DataFrame) -> dict:
    total = len(frame)
    counts = frame[METRIC_COLUMNS].isna().sum().to_dict()
    percentages = {
        metric: round((count / total) * 100, 2) if total else 0.0
        for metric, count in counts.items()
    }
    return {
        "total_rows": total,
        "counts": {key: int(value) for key, value in counts.items()},
        "percentages": percentages,
    }


def range_report(frame: pd.DataFrame) -> dict:
    report = {}
    for metric, (low, high) in METRIC_RANGES.items():
        if metric not in frame.columns:
            continue
        values = frame[metric]
        report[metric] = int(
            ((values < low) | (values > high)).fillna(False).sum()
        )
    return report


def fill_missing(
    frame: pd.DataFrame,
    *,
    method: str = "keep",
    limit: int | None = 2,
) -> pd.DataFrame:
    """Handle missing metric values.

    ``keep`` leaves missing values untouched (the default for analysis).
    ``drop`` removes rows containing any missing metric.
    ``interpolate`` fills gaps within each astronaut's series.
    """

    if method == "keep":
        return frame.copy()

    if method == "drop":
        return frame.dropna(subset=METRIC_COLUMNS).reset_index(drop=True)

    if method != "interpolate":
        raise ValueError("method must be one of: keep, drop, interpolate")

    result = frame.sort_values(
        ["astronaut_id", "recorded_at"], kind="stable"
    ).copy()

    for _, group in result.groupby("astronaut_id", sort=False):
        interpolated = group[METRIC_COLUMNS].interpolate(
            method="linear",
            limit=limit,
            limit_direction="both",
        )
        result.loc[group.index, METRIC_COLUMNS] = interpolated

    return result.reset_index(drop=True)


def build_scaler(method: str = "standard"):
    try:
        return SCALERS[method]()
    except KeyError as error:
        raise ValueError(
            "method must be one of: standard, robust, minmax"
        ) from error


def scale_features(
    frame: pd.DataFrame,
    *,
    columns: Iterable[str] | None = None,
    method: str = "standard",
    scaler=None,
    fit: bool = True,
) -> tuple[pd.DataFrame, object, dict]:
    """Scale selected features while preserving missing values."""

    columns = list(columns or METRIC_COLUMNS)
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {', '.join(missing)}")

    if fit:
        scaler = build_scaler(method)
        values = scaler.fit_transform(frame[columns])
    else:
        if scaler is None:
            raise ValueError("A fitted scaler is required when fit is False")
        values = scaler.transform(frame[columns])

    scaled = pd.DataFrame(values, columns=columns, index=frame.index)

    metadata = {
        "method": method,
        "columns": columns,
        "sample_count": int(len(frame)),
    }

    return scaled, scaler, metadata


def prepare_dataset(
    frame: pd.DataFrame,
    *,
    drop_invalid_identity: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Prepare raw readings for statistical and ML analysis."""

    validate_columns(frame)

    rows_in = int(len(frame))
    work = coerce_types(frame)

    invalid_timestamps = int(work["recorded_at"].isna().sum())
    missing_identity = int(
        (work["astronaut_id"].isna() | (work["astronaut_id"] == "")).sum()
    )

    invalid_identity = work["astronaut_id"].isna() | (
        work["astronaut_id"] == ""
    ) | work["recorded_at"].isna()

    if drop_invalid_identity:
        work = work.loc[~invalid_identity]

    duplicates_removed = int(
        work.duplicated(subset=["astronaut_id", "recorded_at"]).sum()
    )
    work = remove_duplicates(work)
    work = sort_readings(work)

    missing = missing_report(work)
    ranges = range_report(work)

    if len(work):
        date_range = {
            "start": work["recorded_at"].min().isoformat(),
            "end": work["recorded_at"].max().isoformat(),
        }
    else:
        date_range = {"start": None, "end": None}

    report = {
        "rows_in": rows_in,
        "rows_out": int(len(work)),
        "invalid_timestamps": invalid_timestamps,
        "missing_identity": missing_identity,
        "duplicates_removed": duplicates_removed,
        "missing_values": missing["counts"],
        "missing_percentages": missing["percentages"],
        "out_of_range": ranges,
        "astronauts": int(work["astronaut_id"].nunique()),
        "date_range": date_range,
    }

    return work.reset_index(drop=True), report


def summarize_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    records = []
    for astronaut_id, group in frame.groupby("astronaut_id", sort=True):
        records.append({
            "astronaut_id": astronaut_id,
            "readings": int(len(group)),
            "first_reading": group["recorded_at"].min(),
            "last_reading": group["recorded_at"].max(),
            "missing_values": int(group[METRIC_COLUMNS].isna().sum().sum()),
        })
    return pd.DataFrame(records)
