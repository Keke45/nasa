import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.utils import timezone

from baselines.models import HealthReading
from baselines.service import recalculate_baselines

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=60)


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


class MissionDashboardAPITests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.override = override_settings(
            INTELLIGENCE_MODEL_DIR=Path(self.temp_dir.name)
        )
        self.override.enable()
        self.addCleanup(self.override.disable)

        for index in range(20):
            create_reading("AST-DASH-A", index, 60 + (index % 5))
            create_reading("AST-DASH-B", index, 60 + (index % 3))

        recalculate_baselines("AST-DASH-A")
        recalculate_baselines("AST-DASH-B")

        self.stable = create_reading("AST-DASH-B", 20, 60.0)
        self.concerning = create_reading(
            "AST-DASH-A",
            20,
            105.0,
            sleep_duration=3.0,
            fatigue_level=9.0,
            physical_activity=10.0,
        )

    def test_overview_returns_mission_summary(self):
        response = self.client.get("/api/mission/overview")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        summary = body["summary"]

        self.assertEqual(summary["total_astronauts"], 2)
        self.assertEqual(summary["monitored"], 2)
        self.assertGreaterEqual(summary["active_alerts"], 1)
        self.assertGreaterEqual(summary["requiring_attention"], 1)
        self.assertEqual(
            set(summary["severity_counts"]),
            {
                "SEVERE",
                "ANOMALY",
                "WATCH",
                "NORMAL",
                "NOT_EVALUATED",
            },
        )
        self.assertIsNotNone(summary["last_reading_at"])

    def test_overview_astronaut_entries_and_alerts(self):
        response = self.client.get("/api/mission/overview")
        body = response.json()

        entries = {
            entry["astronaut_id"]: entry
            for entry in body["astronauts"]
        }
        self.assertIn("AST-DASH-A", entries)
        self.assertIn("AST-DASH-B", entries)

        concerning = entries["AST-DASH-A"]
        self.assertTrue(concerning["requires_review"])
        self.assertIn(
            concerning["severity"], {"SEVERE", "ANOMALY", "WATCH"}
        )
        self.assertEqual(concerning["reading_count"], 21)
        self.assertEqual(
            concerning["latest_reading"]["id"],
            self.concerning.id,
        )
        self.assertGreaterEqual(len(concerning["alerts"]), 1)
        self.assertIsNone(concerning["error"])

        stable = entries["AST-DASH-B"]
        self.assertFalse(stable["requires_review"])
        self.assertEqual(stable["severity"], "NORMAL")

    def test_alerts_endpoint_exposes_explainable_findings(self):
        response = self.client.get("/api/mission/alerts")

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["summary"]["total"], len(body["alerts"]))
        self.assertGreaterEqual(body["summary"]["total"], 1)
        self.assertGreaterEqual(body["summary"]["astronauts_affected"], 1)

        ranks = {"SEVERE": 4, "ANOMALY": 3, "WATCH": 2, "NORMAL": 1}
        previous_rank = 5
        for alert in body["alerts"]:
            self.assertIn("observation", alert)
            self.assertTrue(alert["observation"])
            self.assertIsInstance(
                alert["contributing_factors"], list
            )
            self.assertEqual(alert["status"], "NEW")
            self.assertEqual(alert["recommended_actions"], [])
            self.assertIn("astronaut_id", alert)
            self.assertIn("current_value", alert)
            self.assertIn("baseline_value", alert)

            rank = ranks.get(alert["severity"], 0)
            self.assertLessEqual(rank, previous_rank)
            previous_rank = rank

    def test_overview_without_readings_is_empty(self):
        HealthReading.objects.all().delete()

        response = self.client.get("/api/mission/overview")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["astronauts"], [])
        self.assertEqual(body["alerts"], [])
        self.assertEqual(body["summary"]["total_astronauts"], 0)
        self.assertEqual(body["summary"]["monitored"], 0)
        self.assertEqual(body["summary"]["active_alerts"], 0)
        self.assertEqual(body["summary"]["requiring_attention"], 0)
        self.assertIsNone(body["summary"]["last_reading_at"])

    def test_alerts_without_readings_is_empty(self):
        HealthReading.objects.all().delete()

        response = self.client.get("/api/mission/alerts")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["alerts"], [])
        self.assertEqual(body["summary"]["total"], 0)
        self.assertEqual(body["summary"]["astronauts_affected"], 0)
