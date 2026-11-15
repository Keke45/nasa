import json
from datetime import datetime, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from baselines.models import BaselineSnapshot, HealthBaseline, HealthReading
from ml.metrics import METRIC_COLUMNS
from services.constants import (
    BASELINE_KIND_LONG_TERM,
    BASELINE_KIND_RECENT,
    STATUS_INSUFFICIENT,
)

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=90)


def reading_payload(astronaut_id="AST-API", day=0, **overrides):
    payload = {
        "astronaut_id": astronaut_id,
        "recorded_at": (START + timedelta(days=day)).isoformat(),
        "heart_rate": 60 + day,
        "systolic_bp": 115,
        "diastolic_bp": 75,
        "body_temperature": 36.6,
        "oxygen_saturation": 98.0,
        "sleep_duration": 7.5,
        "physical_activity": 60,
        "fatigue_level": 3.0,
    }
    payload.update(overrides)
    return payload


def insert_days(astronaut_id="AST-API", days=20):
    HealthReading.objects.bulk_create([
        HealthReading(
            astronaut_id=astronaut_id,
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
        for index in range(days)
    ])


class ReadingAPITests(TestCase):
    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_ingest_single_reading(self):
        response = self.post_json("/api/readings", reading_payload())

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["created"], 1)
        self.assertEqual(HealthReading.objects.count(), 1)
        self.assertEqual(
            HealthReading.objects.get().source, "external"
        )

    def test_ingest_bulk_readings(self):
        payload = {
            "readings": [reading_payload(day=index) for index in range(3)]
        }

        response = self.post_json("/api/readings", payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["created"], 3)
        self.assertEqual(HealthReading.objects.count(), 3)

    def test_duplicate_timestamp_updates_instead_of_creating(self):
        self.post_json("/api/readings", reading_payload(day=0))
        response = self.post_json(
            "/api/readings", reading_payload(day=0, heart_rate=80)
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["updated"], 1)
        self.assertEqual(HealthReading.objects.count(), 1)
        self.assertEqual(HealthReading.objects.get().heart_rate, 80)

    def test_rejects_out_of_range_metric(self):
        response = self.post_json(
            "/api/readings", reading_payload(heart_rate=500)
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(HealthReading.objects.count(), 0)

    def test_rejects_systolic_not_greater_than_diastolic(self):
        response = self.post_json(
            "/api/readings",
            reading_payload(systolic_bp=70, diastolic_bp=90),
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_reading_without_metrics(self):
        response = self.post_json("/api/readings", {
            "astronaut_id": "AST-API",
            "recorded_at": START.isoformat(),
        })

        self.assertEqual(response.status_code, 400)

    def test_list_readings_with_date_filter_and_limit(self):
        insert_days(days=5)

        response = self.client.get(
            "/api/readings/AST-API",
            {
                "start": (START + timedelta(days=1)).isoformat(),
                "end": (START + timedelta(days=4)).isoformat(),
                "limit": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

    def test_list_readings_rejects_invalid_date(self):
        response = self.client.get(
            "/api/readings/AST-API", {"start": "not-a-date"}
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(INTELLIGENCE_INGEST_TOKEN="secret")
    def test_ingest_requires_configured_token(self):
        response = self.post_json("/api/readings", reading_payload())

        self.assertEqual(response.status_code, 401)

    @override_settings(INTELLIGENCE_INGEST_TOKEN="secret")
    def test_ingest_accepts_valid_token(self):
        response = self.client.post(
            "/api/readings",
            data=json.dumps(reading_payload()),
            content_type="application/json",
            HTTP_X_INGEST_TOKEN="secret",
        )

        self.assertEqual(response.status_code, 201)


class BaselineAPITests(TestCase):
    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_calculate_and_list_baselines(self):
        insert_days(days=20)

        response = self.post_json(
            "/api/baselines/AST-API/calculate", {"window_days": 10}
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["created"], len(METRIC_COLUMNS))
        self.assertEqual(body["snapshot"]["window_days"], 10)
        self.assertEqual(body["snapshot"]["reading_count"], 10)
        self.assertEqual(len(body["baselines"]), len(METRIC_COLUMNS))
        self.assertTrue(any(
            "simulated" in warning for warning in body["warnings"]
        ))
        self.assertEqual(
            body["baselines"][0]["sample_count"], 10
        )

        listing = self.client.get("/api/baselines/AST-API")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()["baselines"]), len(METRIC_COLUMNS))

    def test_default_calculation_uses_recent_window(self):
        insert_days(days=40)

        response = self.post_json(
            "/api/baselines/AST-API/calculate", {}
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["snapshot"]["window_days"], 30)
        self.assertEqual(
            response.json()["baselines"][0]["sample_count"], 30
        )

    def test_all_window_calculates_long_term_baseline(self):
        insert_days(days=40)

        response = self.post_json(
            "/api/baselines/AST-API/calculate", {"window_days": "all"}
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["snapshot"]["window_days"])
        self.assertEqual(
            response.json()["snapshot"]["baseline_kind"],
            BASELINE_KIND_LONG_TERM,
        )
        self.assertEqual(
            response.json()["baselines"][0]["sample_count"], 40
        )

    def test_before_boundary_excludes_current_reading(self):
        insert_days(days=10)
        before = START + timedelta(days=9)

        response = self.post_json(
            "/api/baselines/AST-API/calculate",
            {"window_days": None, "before": before.isoformat()},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["baselines"][0]["sample_count"], 9
        )
        self.assertEqual(
            datetime.fromisoformat(
                response.json()["snapshot"]["before"].replace("Z", "+00:00")
            ),
            before,
        )

    def test_kind_filter_returns_no_recent_baselines(self):
        insert_days(days=20)
        self.post_json("/api/baselines/AST-API/calculate", {
            "window_days": None
        })

        recent = self.client.get(
            "/api/baselines/AST-API", {"kind": BASELINE_KIND_RECENT}
        )
        long_term = self.client.get(
            "/api/baselines/AST-API", {"kind": BASELINE_KIND_LONG_TERM}
        )

        self.assertEqual(recent.json()["baselines"], [])
        self.assertEqual(
            len(long_term.json()["baselines"]), len(METRIC_COLUMNS)
        )

    def test_history_returns_snapshot_versions(self):
        insert_days(days=20)
        self.post_json("/api/baselines/AST-API/calculate", {
            "window_days": 10
        })
        self.post_json("/api/baselines/AST-API/calculate", {
            "window_days": 20
        })

        response = self.client.get("/api/baselines/AST-API/history")

        self.assertEqual(response.status_code, 200)
        history = response.json()["history"]
        self.assertEqual([group["snapshot"]["version"] for group in history], [2, 1])
        self.assertEqual(
            len(history[0]["baselines"]), len(METRIC_COLUMNS)
        )

    def test_insufficient_data_produces_warning(self):
        insert_days(days=2)

        response = self.post_json(
            "/api/baselines/AST-API/calculate", {}
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(any(
            "Insufficient data" in warning for warning in body["warnings"]
        ))
        self.assertTrue(all(
            baseline["baseline_status"] == STATUS_INSUFFICIENT
            and baseline["is_usable"] is False
            for baseline in body["baselines"]
        ))

    def test_unknown_metric_is_rejected(self):
        response = self.client.get(
            "/api/baselines/AST-API", {"metric": "unknown"}
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_kind_is_rejected(self):
        response = self.client.get(
            "/api/baselines/AST-API", {"kind": "sometimes"}
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_window_is_rejected(self):
        response = self.client.get(
            "/api/baselines/AST-API/history", {"window_days": "abc"}
        )

        self.assertEqual(response.status_code, 400)

    def test_calculation_creates_snapshot_rows(self):
        insert_days(days=20)

        self.post_json("/api/baselines/AST-API/calculate", {})

        self.assertEqual(
            BaselineSnapshot.objects.filter(
                astronaut_id="AST-API"
            ).count(),
            1,
        )
        snapshot = BaselineSnapshot.objects.get(astronaut_id="AST-API")
        self.assertEqual(snapshot.metric_count, len(METRIC_COLUMNS))
        self.assertEqual(
            HealthBaseline.objects.filter(
                astronaut_id="AST-API", snapshot=snapshot
            ).count(),
            len(METRIC_COLUMNS),
        )
