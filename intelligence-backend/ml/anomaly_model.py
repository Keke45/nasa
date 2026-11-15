"""Per-astronaut unsupervised anomaly models.

Isolation Forest models learn the distribution of an astronaut's own
historical measurements. Scores are statistical signals for review and
are not medical diagnoses.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.metrics import METRIC_COLUMNS, METRIC_LABELS, METRIC_UNITS

MODEL_FORMAT_VERSION = 1
DEFAULT_MIN_SAMPLES = 20
DEFAULT_CONTAMINATION = 0.05
DEFAULT_N_ESTIMATORS = 200
RANDOM_STATE = 42
MIN_FEATURE_VALUES = 2
TOP_DEVIATIONS = 3

STATUS_NORMAL = "NORMAL"
STATUS_ANOMALY = "ANOMALY"
STATUS_NOT_TRAINED = "NOT_TRAINED"
STATUS_NOT_EVALUATED = "NOT_EVALUATED"
STATUS_ERROR = "ERROR"


class AnomalyModelError(Exception):
    pass


class InsufficientTrainingData(AnomalyModelError):
    pass


def _model_dir(model_dir=None) -> Path:
    if model_dir is None:
        return Path(settings.INTELLIGENCE_MODEL_DIR)
    return Path(model_dir)


def model_path(astronaut_id: str, model_dir=None) -> Path:
    safe = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        str(astronaut_id),
    ).strip("._") or "astronaut"
    digest = hashlib.sha256(
        str(astronaut_id).encode("utf-8")
    ).hexdigest()[:12]
    return _model_dir(model_dir) / f"{safe[:48]}-{digest}.joblib"


def _to_timestamp(value):
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


def _to_float(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _read_value(reading, key):
    if isinstance(reading, Mapping):
        return reading.get(key)
    return getattr(reading, key, None)


def _training_rows(readings):
    if isinstance(readings, pd.DataFrame):
        if "recorded_at" not in readings.columns:
            return []
        source = readings.to_dict("records")
    else:
        source = readings

    rows = []
    for reading in source:
        recorded_at = _to_timestamp(_read_value(reading, "recorded_at"))
        if recorded_at is None:
            continue

        values = {
            metric: _to_float(_read_value(reading, metric))
            for metric in METRIC_COLUMNS
        }
        if not any(value is not None for value in values.values()):
            continue

        rows.append({
            "recorded_at": recorded_at,
            **values,
        })

    rows.sort(key=lambda row: row["recorded_at"])
    return rows


def _isoformat(value):
    if value is None:
        return None
    return value.isoformat()


def train_personal_anomaly_model(
    astronaut_id: str,
    readings,
    *,
    contamination: float = DEFAULT_CONTAMINATION,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
) -> dict:
    """Fit an Isolation Forest to one astronaut's historical readings."""

    if not 0 < contamination <= 0.5:
        raise ValueError("contamination must be greater than 0 and at most 0.5")
    if min_samples < 5:
        raise ValueError("min_samples must be at least 5")
    if n_estimators < 10:
        raise ValueError("n_estimators must be at least 10")

    rows = _training_rows(readings)
    if len(rows) < min_samples:
        raise InsufficientTrainingData(
            f"{astronaut_id} has {len(rows)} usable reading(s); "
            f"at least {min_samples} are required."
        )

    frame = pd.DataFrame(rows)
    feature_names = [
        metric
        for metric in METRIC_COLUMNS
        if frame[metric].notna().sum() >= MIN_FEATURE_VALUES
    ]
    if not feature_names:
        raise InsufficientTrainingData(
            "No metric has enough non-missing values for training."
        )

    features = frame[feature_names].to_numpy(dtype=float)
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=RANDOM_STATE,
        )),
    ])
    pipeline.fit(features)

    decision_scores = pipeline.decision_function(features)
    trained_at = timezone.now()

    return {
        "model_format_version": MODEL_FORMAT_VERSION,
        "astronaut_id": str(astronaut_id),
        "model_type": "IsolationForest",
        "model_version": trained_at.strftime("%Y%m%dT%H%M%S%f"),
        "trained_at": trained_at.isoformat(),
        "feature_names": feature_names,
        "pipeline": pipeline,
        "sample_count": len(frame),
        "training_start": _isoformat(frame["recorded_at"].min()),
        "training_end": _isoformat(frame["recorded_at"].max()),
        "contamination": contamination,
        "n_estimators": n_estimators,
        "decision_min": float(np.min(decision_scores)),
        "decision_max": float(np.max(decision_scores)),
        "decision_median": float(np.median(decision_scores)),
    }


def save_personal_anomaly_model(artifact: dict, model_dir=None) -> Path:
    path = model_path(artifact["astronaut_id"], model_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{path.stem}-",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(descriptor)

    try:
        joblib.dump(artifact, temporary_path)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

    return path


def train_and_save_personal_anomaly_model(
    astronaut_id: str,
    readings,
    *,
    model_dir=None,
    **training_options,
) -> tuple[dict, Path]:
    artifact = train_personal_anomaly_model(
        astronaut_id,
        readings,
        **training_options,
    )
    path = save_personal_anomaly_model(artifact, model_dir)
    return artifact, path


def load_personal_anomaly_model(astronaut_id: str, model_dir=None):
    path = model_path(astronaut_id, model_dir)
    if not path.exists():
        return None

    try:
        artifact = joblib.load(path)
    except Exception as error:
        raise AnomalyModelError(
            f"Could not load anomaly model for {astronaut_id}: {error}"
        ) from error

    if not isinstance(artifact, dict):
        raise AnomalyModelError("Stored anomaly model is not valid.")
    if artifact.get("model_format_version") != MODEL_FORMAT_VERSION:
        raise AnomalyModelError("Stored anomaly model format is unsupported.")
    if "pipeline" not in artifact or "feature_names" not in artifact:
        raise AnomalyModelError("Stored anomaly model is incomplete.")

    return artifact


def _reading_vector(reading, feature_names):
    vector = []
    for metric in feature_names:
        value = _to_float(_read_value(reading, metric))
        vector.append(np.nan if value is None else value)
    return vector


def _top_deviations(reading, artifact):
    pipeline = artifact["pipeline"]
    scaler = pipeline.named_steps["scaler"]
    feature_names = artifact["feature_names"]
    deviations = []

    for index, metric in enumerate(feature_names):
        value = _to_float(_read_value(reading, metric))
        if value is None:
            continue

        scale = scaler.scale_[index]
        if not np.isfinite(scale) or scale == 0:
            continue

        z_score = (value - scaler.mean_[index]) / scale
        deviations.append({
            "metric": metric,
            "metric_label": METRIC_LABELS.get(metric, metric),
            "unit": METRIC_UNITS.get(metric, ""),
            "value": value,
            "z_score": float(z_score),
            "absolute_z": abs(float(z_score)),
        })

    deviations.sort(
        key=lambda item: item["absolute_z"],
        reverse=True,
    )
    return deviations[:TOP_DEVIATIONS]


def score_reading(reading, artifact: dict) -> dict:
    """Score one reading with a trained personal model."""

    feature_names = artifact["feature_names"]
    vector = _reading_vector(reading, feature_names)
    missing_metrics = [
        metric
        for metric, value in zip(feature_names, vector)
        if np.isnan(value)
    ]
    present = len(feature_names) - len(missing_metrics)

    metadata = {
        "model_type": artifact.get("model_type"),
        "model_version": artifact.get("model_version"),
        "trained_at": artifact.get("trained_at"),
        "training_start": artifact.get("training_start"),
        "training_end": artifact.get("training_end"),
        "sample_count": artifact.get("sample_count"),
        "contamination": artifact.get("contamination"),
        "feature_names": feature_names,
    }

    if present == 0:
        return {
            "status": STATUS_NOT_EVALUATED,
            "evaluated": False,
            "is_anomaly": None,
            "decision_score": None,
            "anomaly_score": None,
            "in_sample": None,
            "missing_metrics": missing_metrics,
            "top_deviating_metrics": [],
            "model": metadata,
            "reason": (
                "The reading has none of the metrics used by the "
                "personal anomaly model."
            ),
        }

    pipeline = artifact["pipeline"]
    sample = np.array([vector], dtype=float)
    decision_score = float(
        pipeline.decision_function(sample)[0]
    )
    prediction = int(pipeline.predict(sample)[0])

    decision_min = float(artifact["decision_min"])
    decision_max = float(artifact["decision_max"])
    span = decision_max - decision_min
    if span <= 0:
        anomaly_score = 0.5
    else:
        anomaly_score = (
            (decision_max - decision_score) / span
        )
        anomaly_score = float(np.clip(anomaly_score, 0.0, 1.0))

    is_anomaly = prediction == -1
    recorded_at = _to_timestamp(_read_value(reading, "recorded_at"))
    training_end = _to_timestamp(artifact.get("training_end"))
    in_sample = (
        recorded_at is not None
        and training_end is not None
        and recorded_at <= training_end
    )

    if is_anomaly:
        reason = (
            "The personal Isolation Forest flagged this reading as "
            "statistically unusual."
        )
    else:
        reason = (
            "The personal Isolation Forest classified this reading as "
            "consistent with the astronaut's history."
        )

    return {
        "status": STATUS_ANOMALY if is_anomaly else STATUS_NORMAL,
        "evaluated": True,
        "is_anomaly": is_anomaly,
        "decision_score": decision_score,
        "anomaly_score": anomaly_score,
        "in_sample": in_sample,
        "missing_metrics": missing_metrics,
        "top_deviating_metrics": _top_deviations(reading, artifact),
        "model": metadata,
        "reason": reason,
    }


def evaluate_personal_anomaly(
    astronaut_id: str,
    reading,
    *,
    model_dir=None,
) -> dict:
    try:
        artifact = load_personal_anomaly_model(
            astronaut_id,
            model_dir=model_dir,
        )
    except AnomalyModelError as error:
        return {
            "status": STATUS_ERROR,
            "evaluated": False,
            "is_anomaly": None,
            "error": str(error),
        }

    if artifact is None:
        return {
            "status": STATUS_NOT_TRAINED,
            "evaluated": False,
            "is_anomaly": None,
            "reason": (
                "No personal ML anomaly model has been trained for this "
                "astronaut."
            ),
        }

    return score_reading(reading, artifact)
