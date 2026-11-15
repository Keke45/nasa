"""Deterministic simulated astronaut health readings.

The generator creates several fictional astronauts with different health
scenarios so the intelligence engine can be developed and tested without
real mission data. It intentionally includes missing values, duplicate
readings and unusual multi-indicator combinations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml.metrics import METRIC_COLUMNS, METRIC_RANGES, READING_COLUMNS


@dataclass(frozen=True)
class AstronautProfile:
    astronaut_id: str
    scenario: str
    heart_rate: float
    systolic_bp: float
    diastolic_bp: float
    body_temperature: float
    oxygen_saturation: float
    sleep_duration: float
    physical_activity: float
    fatigue_level: float
    missing_rate: float = 0.01


PROFILES = [
    AstronautProfile(
        astronaut_id="AST-001",
        scenario="stable",
        heart_rate=58,
        systolic_bp=115,
        diastolic_bp=74,
        body_temperature=36.50,
        oxygen_saturation=98.6,
        sleep_duration=8.0,
        physical_activity=70,
        fatigue_level=2.5,
    ),
    AstronautProfile(
        astronaut_id="AST-002",
        scenario="rising_heart_rate",
        heart_rate=66,
        systolic_bp=119,
        diastolic_bp=77,
        body_temperature=36.60,
        oxygen_saturation=97.6,
        sleep_duration=7.0,
        physical_activity=50,
        fatigue_level=3.0,
    ),
    AstronautProfile(
        astronaut_id="AST-003",
        scenario="decreasing_sleep_increasing_fatigue",
        heart_rate=62,
        systolic_bp=116,
        diastolic_bp=75,
        body_temperature=36.55,
        oxygen_saturation=98.0,
        sleep_duration=8.4,
        physical_activity=60,
        fatigue_level=2.2,
    ),
    AstronautProfile(
        astronaut_id="AST-004",
        scenario="declining_oxygen",
        heart_rate=70,
        systolic_bp=121,
        diastolic_bp=78,
        body_temperature=36.65,
        oxygen_saturation=97.2,
        sleep_duration=6.6,
        physical_activity=45,
        fatigue_level=3.4,
    ),
    AstronautProfile(
        astronaut_id="AST-005",
        scenario="acute_unusual_combination",
        heart_rate=60,
        systolic_bp=115,
        diastolic_bp=73,
        body_temperature=36.50,
        oxygen_saturation=98.3,
        sleep_duration=7.3,
        physical_activity=58,
        fatigue_level=2.8,
    ),
    AstronautProfile(
        astronaut_id="AST-006",
        scenario="missing_readings",
        heart_rate=64,
        systolic_bp=117,
        diastolic_bp=76,
        body_temperature=36.60,
        oxygen_saturation=98.3,
        sleep_duration=7.8,
        physical_activity=65,
        fatigue_level=2.4,
        missing_rate=0.12,
    ),
]

NOISE = {
    "heart_rate": 3.5,
    "systolic_bp": 5.0,
    "diastolic_bp": 3.5,
    "body_temperature": 0.15,
    "oxygen_saturation": 0.6,
    "sleep_duration": 0.7,
    "physical_activity": 12.0,
    "fatigue_level": 0.9,
}

DEFAULT_START = datetime(2026, 8, 1, 7, 0, tzinfo=timezone.utc)
DEFAULT_DAYS = 90


def _clip(values: np.ndarray, metric: str) -> np.ndarray:
    low, high = METRIC_RANGES[metric]
    return np.clip(values, low, high)


def _apply_scenario(
    frame: pd.DataFrame,
    profile: AstronautProfile,
) -> pd.DataFrame:
    day = np.arange(len(frame))
    scenario = profile.scenario

    if scenario == "rising_heart_rate":
        ramp = np.clip((day - 30) / 45, 0, 1)
        frame["heart_rate"] += 20 * ramp
        frame["fatigue_level"] += 1.5 * ramp
        frame["systolic_bp"] += 6 * ramp

    elif scenario == "decreasing_sleep_increasing_fatigue":
        ramp = np.clip((day - 20) / 50, 0, 1)
        frame["sleep_duration"] -= 3.5 * ramp
        frame["fatigue_level"] += 5.0 * ramp
        frame["heart_rate"] += 8 * ramp
        frame["physical_activity"] -= 20 * ramp

    elif scenario == "declining_oxygen":
        ramp = np.clip((day - 25) / 50, 0, 1)
        frame["oxygen_saturation"] -= 5.0 * ramp
        frame["heart_rate"] += 12 * ramp
        frame["fatigue_level"] += 2.5 * ramp

    elif scenario == "acute_unusual_combination":
        event = (day >= 50) & (day <= 56)
        severity = np.where(event, np.sin((day - 50) / 6 * np.pi), 0.0)
        frame["heart_rate"] += 28 * severity
        frame["body_temperature"] += 1.1 * severity
        frame["oxygen_saturation"] -= 3.5 * severity
        frame["sleep_duration"] -= 2.0 * severity
        frame["fatigue_level"] += 4.5 * severity
        frame["physical_activity"] -= 25 * severity

    return frame


def generate_astronaut_series(
    profile: AstronautProfile,
    *,
    days: int = DEFAULT_DAYS,
    start: datetime = DEFAULT_START,
    seed: int = 42,
    missing_rate: float | None = None,
) -> pd.DataFrame:
    """Generate one reading per day for a single astronaut."""

    if days < 1:
        raise ValueError("days must be at least 1")

    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({
        "astronaut_id": profile.astronaut_id,
        "recorded_at": [start + timedelta(days=offset) for offset in range(days)],
    })

    for metric, noise in NOISE.items():
        baseline = getattr(profile, metric)
        values = rng.normal(baseline, noise, days)
        frame[metric] = _clip(values, metric)

    frame = _apply_scenario(frame, profile)

    for metric in METRIC_COLUMNS:
        frame[metric] = _clip(frame[metric].to_numpy(dtype=float), metric)

    rate = profile.missing_rate if missing_rate is None else missing_rate
    if rate > 0:
        missing_mask = rng.random((days, len(METRIC_COLUMNS))) < rate
        for column_index, metric in enumerate(METRIC_COLUMNS):
            frame.loc[missing_mask[:, column_index], metric] = np.nan

    frame = frame[READING_COLUMNS]

    return frame.round({
        "heart_rate": 0,
        "systolic_bp": 0,
        "diastolic_bp": 0,
        "body_temperature": 1,
        "oxygen_saturation": 1,
        "sleep_duration": 1,
        "physical_activity": 0,
        "fatigue_level": 1,
    })


def generate_sample_data(
    *,
    days: int = DEFAULT_DAYS,
    start: datetime = DEFAULT_START,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate readings for all fictional astronauts.

    Includes:
    - stable measurements
    - increasing heart rate
    - decreasing sleep and increasing fatigue
    - declining oxygen saturation
    - an acute unusual combination of readings
    - missing readings and duplicate rows
    """

    frames = [
        generate_astronaut_series(
            profile,
            days=days,
            start=start,
            seed=seed + index,
        )
        for index, profile in enumerate(PROFILES)
    ]

    data = pd.concat(frames, ignore_index=True)

    missing_profile = next(p for p in PROFILES if p.scenario == "missing_readings")
    gap_start = start + timedelta(days=40)
    gap_end = start + timedelta(days=46)
    gap = (
        (data["astronaut_id"] == missing_profile.astronaut_id)
        & (data["recorded_at"] >= gap_start)
        & (data["recorded_at"] <= gap_end)
    )
    data = data.loc[~gap].reset_index(drop=True)

    duplicate_rows = data.sample(n=6, random_state=seed)
    data = pd.concat([data, duplicate_rows], ignore_index=True)

    return data.sort_values(
        ["astronaut_id", "recorded_at"], kind="stable"
    ).reset_index(drop=True)


def write_sample_csv(
    path: str | Path | None = None,
    *,
    days: int = DEFAULT_DAYS,
    seed: int = 42,
) -> Path:
    if path is None:
        path = Path(__file__).resolve().parent / "data" / "sample_health_readings.csv"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = generate_sample_data(days=days, seed=seed)
    data.to_csv(path, index=False)

    return path


if __name__ == "__main__":
    csv_path = write_sample_csv()
    dataset = generate_sample_data()
    print(f"Wrote {len(dataset)} readings to {csv_path}")
    print(dataset.groupby("astronaut_id").size().to_string())
