"""Shared definitions for astronaut health measurements."""

METRIC_COLUMNS = [
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "body_temperature",
    "oxygen_saturation",
    "sleep_duration",
    "physical_activity",
    "fatigue_level",
]

METRIC_LABELS = {
    "heart_rate": "Heart rate",
    "systolic_bp": "Systolic blood pressure",
    "diastolic_bp": "Diastolic blood pressure",
    "body_temperature": "Body temperature",
    "oxygen_saturation": "Oxygen saturation",
    "sleep_duration": "Sleep duration",
    "physical_activity": "Physical activity",
    "fatigue_level": "Fatigue level",
}

METRIC_UNITS = {
    "heart_rate": "bpm",
    "systolic_bp": "mmHg",
    "diastolic_bp": "mmHg",
    "body_temperature": "C",
    "oxygen_saturation": "%",
    "sleep_duration": "hours",
    "physical_activity": "minutes/day",
    "fatigue_level": "score (1-10)",
}

METRIC_RANGES = {
    "heart_rate": (30.0, 220.0),
    "systolic_bp": (60.0, 250.0),
    "diastolic_bp": (30.0, 160.0),
    "body_temperature": (33.0, 43.0),
    "oxygen_saturation": (50.0, 100.0),
    "sleep_duration": (0.0, 24.0),
    "physical_activity": (0.0, 600.0),
    "fatigue_level": (1.0, 10.0),
}

READING_COLUMNS = ["astronaut_id", "recorded_at", *METRIC_COLUMNS]
