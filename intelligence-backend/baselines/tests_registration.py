import json
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from baselines.models import HealthReading


def registration_payload(
    astronaut_id="AST-REG",
    *,
    recorded_at=None,
    **health_overrides,
):
    health = {
        "height_cm": 180.0,
        "weight_kg": 75.0,
        "resting_heart_rate": 62.0,
        "systolic_bp": 118.0,
        "diastolic_bp": 76.0,
        "oxygen_saturation": 98.5,
        "body_temperature": 36.7,
    }
    health.update(health_overrides)

    payload = {
        "personal": {
            "astronaut_id": astronaut_id,
            "full_name": "Test Astronaut",
            "date_of_birth": "1990-01-01",
            "nationality": "US",
        },
        "mission": {
            "mission_name": "Test Mission",
            "mission_role": "Commander",
            "start_date": "2027-01-01",
            "expected_return_date": "2027-06-01",
        },
        "health": health,
        "account": {
            "username": "test.astronaut",
            "initial_password": "not-stored-here",
        },
    }
    if recorded_at is not None:
        payload["recorded_at"] = recorded_at.isoformat()
    return payload


class RegistrationIntakeTests(TestCase):
    def post_json(self, payload, **headers):
        return self.client.post(
            "/api/registrations",
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    def test_registration_creates_initial_reading(self):
        response = self.post_json(registration_payload())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["created"])
        self.assertEqual(body["astronaut_id"], "AST-REG")
        self.assertEqual(
            body["reading"]["source"], "registration"
        )
        self.assertEqual(
            body["reading"]["heart_rate"], 62.0
        )
        self.assertEqual(body["reading"]["systolic_bp"], 118.0)
        self.assertEqual(body["reading"]["diastolic_bp"], 76.0)
        self.assertEqual(
            body["reading"]["oxygen_saturation"], 98.5
        )
        self.assertEqual(
            body["reading"]["body_temperature"], 36.7
        )
        self.assertIsNone(body["reading"]["sleep_duration"])
        self.assertIsNone(body["reading"]["physical_activity"])
        self.assertIsNone(body["reading"]["fatigue_level"])
        self.assertEqual(body["baseline"]["readings_available"], 1)
        self.assertTrue(body["baseline"]["calculation_required"])
        self.assertEqual(
            set(body["missing_metrics"]),
            {"sleep_duration", "physical_activity", "fatigue_level"},
        )
        self.assertTrue(any(
            "at least 5" in warning for warning in body["warnings"]
        ))

        reading = HealthReading.objects.get()
        self.assertEqual(reading.astronaut_id, "AST-REG")
        self.assertEqual(reading.source, "registration")

    def test_registration_is_idempotent_without_timestamp(self):
        first = self.post_json(registration_payload())
        first_time = first.json()["reading"]["recorded_at"]

        second = self.post_json(
            registration_payload(resting_heart_rate=65.0)
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["created"])
        self.assertEqual(
            second.json()["reading"]["recorded_at"], first_time
        )
        self.assertEqual(HealthReading.objects.count(), 1)
        self.assertEqual(
            HealthReading.objects.get().heart_rate, 65.0
        )

    def test_explicit_recorded_at_is_kept(self):
        recorded_at = timezone.now().replace(
            hour=8, minute=0, second=0, microsecond=0
        ) - timedelta(days=2)

        response = self.post_json(
            registration_payload(recorded_at=recorded_at)
        )

        self.assertEqual(response.status_code, 201)
        reading = HealthReading.objects.get()
        self.assertEqual(reading.recorded_at, recorded_at)

    def test_future_recorded_at_is_rejected(self):
        response = self.post_json(registration_payload(
            recorded_at=timezone.now() + timedelta(days=5)
        ))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(HealthReading.objects.count(), 0)

    def test_registration_validation(self):
        cases = [
            registration_payload(astronaut_id="   "),
            registration_payload(resting_heart_rate=500),
            registration_payload(systolic_bp=70, diastolic_bp=90),
        ]

        for payload in cases:
            with self.subTest(payload=payload):
                response = self.post_json(payload)
                self.assertEqual(response.status_code, 400)

        self.assertEqual(HealthReading.objects.count(), 0)

    def test_health_data_is_required(self):
        payload = registration_payload()
        payload["health"] = {"height_cm": 180.0, "weight_kg": 75.0}

        response = self.post_json(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(HealthReading.objects.count(), 0)

    @override_settings(INTELLIGENCE_INGEST_TOKEN="secret")
    def test_registration_requires_configured_token(self):
        response = self.post_json(registration_payload())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(HealthReading.objects.count(), 0)

        response = self.post_json(
            registration_payload(),
            HTTP_X_INGEST_TOKEN="secret",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(HealthReading.objects.count(), 1)
