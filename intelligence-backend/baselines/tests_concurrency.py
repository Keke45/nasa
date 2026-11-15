import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone

from baselines.models import BaselineSnapshot, HealthReading
from baselines.service import get_current_baselines, recalculate_baselines
from ml.metrics import METRIC_COLUMNS

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=40)


class BaselineConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        HealthReading.objects.bulk_create([
            HealthReading(
                astronaut_id="AST-CONCURRENT",
                recorded_at=START + timedelta(days=index),
                heart_rate=60 + index,
                systolic_bp=115,
                diastolic_bp=75,
                body_temperature=36.6,
                oxygen_saturation=98.0,
                sleep_duration=7.5,
                physical_activity=60,
                fatigue_level=3.0,
            )
            for index in range(20)
        ])

    def _run_recalculation(self, barrier, errors):
        try:
            barrier.wait(timeout=10)
            recalculate_baselines("AST-CONCURRENT")
        except Exception as error:
            errors.append(error)
        finally:
            connections.close_all()

    def test_simultaneous_recalculations_allocate_distinct_versions(self):
        barrier = threading.Barrier(2)
        errors = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    self._run_recalculation,
                    barrier,
                    errors,
                )
                for _ in range(2)
            ]
            for future in futures:
                future.result(timeout=30)

        self.assertEqual(errors, [])

        snapshots = list(
            BaselineSnapshot.objects
            .filter(astronaut_id="AST-CONCURRENT")
            .order_by("version")
        )
        current = list(get_current_baselines("AST-CONCURRENT"))

        self.assertEqual([snapshot.version for snapshot in snapshots], [1, 2])
        self.assertEqual(len(current), len(METRIC_COLUMNS))
        self.assertEqual(
            {baseline.baseline_version for baseline in current},
            {2},
        )
        self.assertEqual(
            len({baseline.snapshot_id for baseline in current}),
            1,
        )
        self.assertEqual(
            len({baseline.metric for baseline in current}),
            len(METRIC_COLUMNS),
        )
