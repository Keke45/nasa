from datetime import timedelta

import pandas as pd
from django.test import TestCase
from django.utils import timezone

from baselines.models import HealthBaseline, HealthReading
from baselines.service import (
    get_baseline_history,
    get_current_baselines,
    get_current_versions,
    load_readings,
    recalculate_baselines,
)
from ml.metrics import METRIC_COLUMNS
from services.baseline_service import (
    DEFAULT_ROLLING_WINDOW_DAYS,
    STATUS_ESTABLISHED,
    STATUS_INSUFFICIENT,
    STATUS_PROVISIONAL,
    classify_baseline_status,
    rolling_average_series,
)

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=40)


def build_frame(
    astronaut_id="AST-TEST",
    days=20,
    *,
    heart_rate=None,
    start=START,
    missing_heart_rate=(),
):
    rows = []
    for index in range(days):
        hr = heart_rate[index] if heart_rate is not None else 60 + index
        if index in missing_heart_rate:
            hr = None

        rows.append({
            "astronaut_id": astronaut_id,
            "recorded_at": start + timedelta(days=index),
            "heart_rate": hr,
            "systolic_bp": 115,
            "diastolic_bp": 75,
            "body_temperature": 36.6,
            "oxygen_saturation": 98.0,
            "sleep_duration": 7.5,
            "physical_activity": 60,
            "fatigue_level": 3.0,
        })

    return pd.DataFrame(rows)


def insert_frame(frame):
    records = []
    for row in frame.to_dict("records"):
        records.append(HealthReading(
            astronaut_id=row["astronaut_id"],
            recorded_at=row["recorded_at"],
            **{
                metric: (
                    None if pd.isna(row[metric]) else float(row[metric])
                )
                for metric in METRIC_COLUMNS
            },
        ))
    HealthReading.objects.bulk_create(records)


class BaselineComputationTests(TestCase):
    def test_status_thresholds(self):
        self.assertEqual(classify_baseline_status(0), STATUS_INSUFFICIENT)
        self.assertEqual(classify_baseline_status(4), STATUS_INSUFFICIENT)
        self.assertEqual(classify_baseline_status(5), STATUS_PROVISIONAL)
        self.assertEqual(classify_baseline_status(13), STATUS_PROVISIONAL)
        self.assertEqual(classify_baseline_status(14), STATUS_ESTABLISHED)

    def test_calculates_every_metric(self):
        insert_frame(build_frame(days=20))

        baselines = recalculate_baselines("AST-TEST")

        self.assertEqual(len(baselines), len(METRIC_COLUMNS))
        self.assertEqual(
            {baseline.metric for baseline in baselines},
            set(METRIC_COLUMNS),
        )
        for baseline in baselines:
            self.assertEqual(baseline.sample_count, 20)
            self.assertEqual(baseline.baseline_status, STATUS_ESTABLISHED)
            self.assertEqual(baseline.baseline_version, 1)
            self.assertTrue(baseline.is_current)

    def test_heart_rate_statistics(self):
        insert_frame(build_frame(days=20))

        recalculate_baselines("AST-TEST")
        baseline = HealthBaseline.objects.get(
            astronaut_id="AST-TEST", metric="heart_rate"
        )

        expected = pd.Series(range(60, 80), dtype=float)

        self.assertAlmostEqual(baseline.baseline_value, expected.mean())
        self.assertAlmostEqual(baseline.median_value, expected.median())
        self.assertAlmostEqual(baseline.std_dev, expected.std(ddof=1))
        self.assertAlmostEqual(baseline.min_value, 60.0)
        self.assertAlmostEqual(baseline.max_value, 79.0)
        self.assertAlmostEqual(
            baseline.rolling_average,
            expected.tail(DEFAULT_ROLLING_WINDOW_DAYS).mean(),
        )

    def test_empty_history_creates_insufficient_baselines(self):
        baselines = recalculate_baselines("AST-UNKNOWN")

        self.assertEqual(len(baselines), len(METRIC_COLUMNS))
        for baseline in baselines:
            self.assertEqual(baseline.sample_count, 0)
            self.assertEqual(baseline.baseline_status, STATUS_INSUFFICIENT)
            self.assertIsNone(baseline.baseline_value)
            self.assertIsNone(baseline.std_dev)
            self.assertIsNone(baseline.rolling_average)

    def test_rolling_average_series(self):
        frame = build_frame(days=10)

        result = rolling_average_series(frame, "AST-TEST", "heart_rate", window_days=3)

        self.assertAlmostEqual(result["heart_rate_rolling_average"].iloc[0], 60)
        self.assertAlmostEqual(result["heart_rate_rolling_average"].iloc[2], 61)
        self.assertAlmostEqual(result["heart_rate_rolling_average"].iloc[-1], 68)

    def test_window_limits_analysis(self):
        insert_frame(build_frame(days=20))

        recalculate_baselines("AST-TEST", window_days=7)
        baseline = HealthBaseline.objects.get(
            astronaut_id="AST-TEST", metric="heart_rate"
        )

        self.assertEqual(baseline.sample_count, 7)
        self.assertEqual(baseline.window_days, 7)
        self.assertAlmostEqual(baseline.baseline_value, 76.0)

    def test_missing_values_reduce_metric_sample_count(self):
        insert_frame(build_frame(days=10, missing_heart_rate=(2, 5)))

        recalculate_baselines("AST-TEST")

        heart_rate = HealthBaseline.objects.get(
            astronaut_id="AST-TEST", metric="heart_rate"
        )
        sleep = HealthBaseline.objects.get(
            astronaut_id="AST-TEST", metric="sleep_duration"
        )

        self.assertEqual(heart_rate.sample_count, 8)
        self.assertEqual(heart_rate.baseline_status, STATUS_PROVISIONAL)
        self.assertEqual(sleep.sample_count, 10)

    def test_unusual_reading_is_retained(self):
        heart_rate = [60] * 9 + [160]
        insert_frame(build_frame(days=10, heart_rate=heart_rate))

        recalculate_baselines("AST-TEST")
        baseline = HealthBaseline.objects.get(
            astronaut_id="AST-TEST", metric="heart_rate"
        )

        self.assertEqual(baseline.sample_count, 10)
        self.assertAlmostEqual(baseline.max_value, 160.0)
        self.assertAlmostEqual(baseline.baseline_value, 70.0)


class BaselineVersioningTests(TestCase):
    def test_recalculation_creates_new_version(self):
        insert_frame(build_frame(days=20))

        recalculate_baselines("AST-TEST")
        recalculate_baselines("AST-TEST")

        history = get_baseline_history("AST-TEST", metric="heart_rate")
        current = get_current_baselines("AST-TEST")

        self.assertEqual(history.count(), 2)
        self.assertEqual(history[0].baseline_version, 2)
        self.assertTrue(history[0].is_current)
        self.assertEqual(history[1].baseline_version, 1)
        self.assertFalse(history[1].is_current)
        self.assertTrue(all(b.baseline_version == 2 for b in current))
        self.assertEqual(
            get_current_versions("AST-TEST")["heart_rate"],
            2,
        )

    def test_loader_returns_only_requested_astronaut(self):
        insert_frame(build_frame("AST-A", days=5))
        insert_frame(build_frame("AST-B", days=5))

        frame = load_readings("AST-A")

        self.assertEqual(len(frame), 5)
        self.assertEqual(set(frame["astronaut_id"]), {"AST-A"})

    def test_provisional_status_is_stored(self):
        insert_frame(build_frame("AST-PROV", days=8))

        recalculate_baselines("AST-PROV")

        current = get_current_baselines("AST-PROV")
        self.assertTrue(current)
        self.assertTrue(all(
            baseline.baseline_status == STATUS_PROVISIONAL
            for baseline in current
        ))

    def test_insufficient_status_is_stored(self):
        insert_frame(build_frame("AST-LOW", days=3))

        recalculate_baselines("AST-LOW")

        current = get_current_baselines("AST-LOW")
        self.assertTrue(current)
        self.assertTrue(all(
            baseline.baseline_status == STATUS_INSUFFICIENT
            for baseline in current
        ))
