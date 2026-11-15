import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.utils import timezone

from baselines.models import HealthReading
from baselines.service import recalculate_baselines
from ml.metrics import METRIC_COLUMNS
from services.anomaly_service import SEVERITY_NORMAL

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=40)


def create_reading(astronaut_id, offset_days, heart_rate, **overrides):
    values = {
        "heart_rate": heart_rate,
        "systolic_bp": 115.0,
        "diastolic_bp": 75.0,
        "body_temperature": 36.6,
        "oxygen_saturation": 98.0,
        "sleep_duration": 7.5,
        "physical_activity": 60.0,
        "fatigue_level": 3.0,
    }
    values.update(overrides)
    return HealthReading.objects.create(
        astronaut_id=astronaut_id,
        recorded_at=START + timedelta(days=offset_days),
        source="external",
        **values,
    )


class StatisticalAnalysisAPITests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.override = override_settings(
            INTELLIGENCE_MODEL_DIR=Path(self.temp_dir.name)
        )
        self.override.enable()
        self.addCleanup(self.override.disable)

        for index in range(20):
            create_reading("AST-ANALYSIS", index, 60 + index)

        recalculate_baselines("AST-ANALYSIS")
        self.current = create_reading(
            "AST-ANALYSIS", 20, 100.0
        )

    def get_analysis(self, astronaut_id="AST-ANALYSIS", **params):
        return self.client.get(
            f"/api/analysis/{astronaut_id}",
            params,
        )

    def test_analysis_endpoint_returns_all_sections(self):
        response = self.get_analysis()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["astronaut_id"], "AST-ANALYSIS")
        self.assertEqual(body["reading"]["id"], self.current.id)
        self.assertEqual(body["baseline"]["usable_count"], 8)
        self.assertEqual(len(body["comparisons"]), len(METRIC_COLUMNS))
        self.assertEqual(len(body["anomalies"]), len(METRIC_COLUMNS))
        self.assertEqual(len(body["trends"]), len(METRIC_COLUMNS))
        self.assertTrue(body["summary"]["requires_review"])
        self.assertIn("anomaly", body["summary"])
        self.assertIn("trend_directions", body["summary"])

    def test_reading_id_and_as_of_selectors(self):
        first = HealthReading.objects.filter(
            astronaut_id="AST-ANALYSIS"
        ).order_by("recorded_at").first()

        by_id = self.get_analysis(reading_id=first.id)
        by_as_of = self.get_analysis(as_of=first.recorded_at.isoformat())

        self.assertEqual(by_id.status_code, 200)
        self.assertEqual(by_as_of.status_code, 200)
        self.assertEqual(by_id.json()["reading"]["id"], first.id)
        self.assertEqual(by_as_of.json()["reading"]["id"], first.id)

    def test_conflicting_reading_selectors(self):
        response = self.get_analysis(
            reading_id=self.current.id,
            as_of=self.current.recorded_at.isoformat(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("either reading_id or as_of", str(response.json()))

    def test_missing_astronaut_returns_404(self):
        response = self.get_analysis("AST-MISSING")

        self.assertEqual(response.status_code, 404)

    def test_missing_reading_id_returns_404(self):
        response = self.get_analysis(reading_id=999999)

        self.assertEqual(response.status_code, 404)

    def test_invalid_query_parameters(self):
        cases = [
            {"baseline_kind": "UNKNOWN"},
            {"lookback_days": 0},
            {"short_window_days": 31},
            {"lookback_days": 10},
            {"watch_z": -1},
            {"watch_z": 4, "anomaly_z": 3, "severe_z": 5},
            {"reading_id": "not-an-integer"},
        ]

        for params in cases:
            with self.subTest(params=params):
                response = self.get_analysis(**params)
                self.assertEqual(response.status_code, 400)

    def test_custom_thresholds_are_applied(self):
        default = self.get_analysis()
        relaxed = self.get_analysis(
            watch_z=6,
            anomaly_z=7,
            severe_z=8,
            moving_average_z=6,
        )

        default_hr = next(
            item
            for item in default.json()["anomalies"]
            if item["metric"] == "heart_rate"
        )
        relaxed_hr = next(
            item
            for item in relaxed.json()["anomalies"]
            if item["metric"] == "heart_rate"
        )

        self.assertEqual(default.status_code, 200)
        self.assertEqual(relaxed.status_code, 200)
        self.assertNotEqual(default_hr["severity"], SEVERITY_NORMAL)
        self.assertEqual(relaxed_hr["severity"], SEVERITY_NORMAL)

    def test_lookback_limits_trend_history(self):
        response = self.get_analysis(
            lookback_days=5,
            short_window_days=3,
            long_window_days=5,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["trends"]["heart_rate"]["sample_count"],
            6,
        )

    def test_ml_anomaly_can_be_disabled(self):
        default = self.get_analysis()
        disabled = self.get_analysis(include_ml="false")

        self.assertEqual(default.status_code, 200)
        self.assertEqual(
            default.json()["ml_anomaly"]["status"],
            "NOT_TRAINED",
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(
            disabled.json()["ml_anomaly"]["status"],
            "DISABLED",
        )
        self.assertNotIn(
            "ML anomaly model",
            " ".join(disabled.json()["warnings"]),
        )

    def test_analysis_without_current_baselines(self):
        response = self.get_analysis(baseline_kind="LONG_TERM")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["baseline"]["metric_count"], 0)
        self.assertTrue(any(
            "No current baselines" in warning
            for warning in response.json()["warnings"]
        ))
