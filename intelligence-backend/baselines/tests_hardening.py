from datetime import timedelta

import pandas as pd
from django.test import TestCase
from django.utils import timezone

from baselines.models import BaselineSnapshot, HealthBaseline, HealthReading
from baselines.service import (
    get_current_baselines,
    get_current_snapshot,
    get_usable_baselines,
    recalculate_baselines,
)
from ml.metrics import METRIC_COLUMNS
from services.constants import (
    BASELINE_KIND_LONG_TERM,
    BASELINE_KIND_RECENT,
    DEFAULT_RECENT_WINDOW_DAYS,
    STATUS_ESTABLISHED,
    STATUS_INSUFFICIENT,
    STATUS_PROVISIONAL,
)

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=90)


def build_frame(days=20, *, heart_rate=None, missing_heart_rate=()):
    rows = []
    for index in range(days):
        hr = heart_rate[index] if heart_rate is not None else 60 + index
        if index in missing_heart_rate:
            hr = None
        rows.append({
            "astronaut_id": "AST-HARD",
            "recorded_at": START + timedelta(days=index),
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


def insert_frame(frame, source="simulated"):
    HealthReading.objects.bulk_create([
        HealthReading(
            astronaut_id=row["astronaut_id"],
            recorded_at=row["recorded_at"],
            source=source,
            **{
                metric: (
                    None if pd.isna(row[metric]) else float(row[metric])
                )
                for metric in METRIC_COLUMNS
            },
        )
        for row in frame.to_dict("records")
    ])


class BaselineHardeningTests(TestCase):
    def test_default_window_is_recent_30_days(self):
        insert_frame(build_frame(days=60))

        recalculate_baselines("AST-HARD")

        baseline = HealthBaseline.objects.get(
            astronaut_id="AST-HARD", metric="heart_rate"
        )
        snapshot = get_current_snapshot("AST-HARD")

        self.assertEqual(baseline.sample_count, DEFAULT_RECENT_WINDOW_DAYS)
        self.assertEqual(baseline.window_days, DEFAULT_RECENT_WINDOW_DAYS)
        self.assertEqual(baseline.baseline_kind, BASELINE_KIND_RECENT)
        self.assertEqual(snapshot.window_days, DEFAULT_RECENT_WINDOW_DAYS)
        self.assertEqual(
            snapshot.reading_count, DEFAULT_RECENT_WINDOW_DAYS
        )

    def test_long_term_window_uses_all_history(self):
        insert_frame(build_frame(days=60))

        recalculate_baselines("AST-HARD", window_days=None)

        baseline = HealthBaseline.objects.get(
            astronaut_id="AST-HARD", metric="heart_rate"
        )
        snapshot = get_current_snapshot("AST-HARD")

        self.assertEqual(baseline.sample_count, 60)
        self.assertIsNone(baseline.window_days)
        self.assertEqual(baseline.baseline_kind, BASELINE_KIND_LONG_TERM)
        self.assertIsNone(snapshot.window_days)
        self.assertEqual(snapshot.baseline_kind, BASELINE_KIND_LONG_TERM)

    def test_before_boundary_is_exclusive(self):
        insert_frame(build_frame(days=20))
        before = START + timedelta(days=10)

        recalculate_baselines("AST-HARD", window_days=None, before=before)

        baseline = HealthBaseline.objects.get(
            astronaut_id="AST-HARD", metric="heart_rate"
        )
        snapshot = get_current_snapshot("AST-HARD")

        self.assertEqual(baseline.sample_count, 10)
        self.assertEqual(snapshot.before, before)
        self.assertEqual(snapshot.reading_count, 10)
        self.assertEqual(snapshot.data_end, before - timedelta(days=1))

    def test_calendar_rolling_average_handles_gap(self):
        frame = build_frame(days=5, heart_rate=[60, 61, 62, 63, 64])
        extra = build_frame(days=1, heart_rate=[100])
        extra["recorded_at"] = START + timedelta(days=20)
        frame = pd.concat([frame, extra], ignore_index=True)
        insert_frame(frame)

        recalculate_baselines("AST-HARD", window_days=None)

        baseline = HealthBaseline.objects.get(
            astronaut_id="AST-HARD", metric="heart_rate"
        )

        self.assertEqual(baseline.sample_count, 6)
        self.assertAlmostEqual(baseline.rolling_average, 100.0)
        self.assertEqual(baseline.rolling_sample_count, 1)

    def test_snapshot_links_every_baseline(self):
        insert_frame(build_frame(days=20))

        recalculate_baselines("AST-HARD")

        snapshot = get_current_snapshot("AST-HARD")
        baselines = get_current_baselines("AST-HARD")

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.metric_count, len(METRIC_COLUMNS))
        self.assertEqual(snapshot.reading_count, 20)
        self.assertEqual(
            snapshot.status_summary,
            {STATUS_ESTABLISHED: len(METRIC_COLUMNS)},
        )
        self.assertTrue(all(
            baseline.snapshot_id == snapshot.id for baseline in baselines
        ))

    def test_snapshot_versioning_retains_history(self):
        insert_frame(build_frame(days=20))

        recalculate_baselines("AST-HARD")
        recalculate_baselines("AST-HARD")

        snapshots = list(
            BaselineSnapshot.objects
            .filter(astronaut_id="AST-HARD")
            .order_by("-version")
        )
        current = get_current_baselines("AST-HARD")

        self.assertEqual([s.version for s in snapshots], [2, 1])
        self.assertTrue(all(b.baseline_version == 2 for b in current))
        self.assertTrue(all(b.snapshot_id == snapshots[0].id for b in current))

    def test_is_usable_reflects_status(self):
        insert_frame(build_frame(days=3))
        recalculate_baselines("AST-HARD")
        insufficient = get_current_baselines("AST-HARD").first()
        self.assertFalse(insufficient.is_usable)
        self.assertEqual(insufficient.baseline_status, STATUS_INSUFFICIENT)

        recalculate_baselines(
            "AST-HARD", window_days=None, frame=build_frame(days=8)
        )
        provisional = get_current_baselines("AST-HARD").first()
        self.assertTrue(provisional.is_usable)
        self.assertEqual(provisional.baseline_status, STATUS_PROVISIONAL)

    def test_usable_helper_excludes_insufficient(self):
        insert_frame(build_frame(
            days=6, missing_heart_rate=(0, 1, 2, 3, 4, 5)
        ))
        recalculate_baselines("AST-HARD", window_days=None)

        usable = get_usable_baselines("AST-HARD")

        self.assertNotIn("heart_rate", [b.metric for b in usable])
        self.assertEqual(len(usable), len(METRIC_COLUMNS) - 1)
