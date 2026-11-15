import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from baselines.models import HealthReading
from baselines.service import recalculate_baselines
from ml.anomaly_model import (
    InsufficientTrainingData,
    STATUS_ANOMALY,
    STATUS_ERROR,
    STATUS_NORMAL,
    STATUS_NOT_EVALUATED,
    STATUS_NOT_TRAINED,
    evaluate_personal_anomaly,
    load_personal_anomaly_model,
    model_path,
    score_reading,
    train_and_save_personal_anomaly_model,
    train_personal_anomaly_model,
)
from services.statistical_service import analyze_statistics

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=45)


def training_frame(days=30, astronaut_id="AST-ML"):
    rows = []
    for index in range(days):
        rows.append({
            "astronaut_id": astronaut_id,
            "recorded_at": START + timedelta(days=index),
            "heart_rate": 62 + (index % 5),
            "systolic_bp": 116 + (index % 4),
            "diastolic_bp": 75 + (index % 3),
            "body_temperature": 36.6 + (index % 3) * 0.1,
            "oxygen_saturation": 98.0 - (index % 2) * 0.5,
            "sleep_duration": 7.0 + (index % 3) * 0.3,
            "physical_activity": 60 + (index % 5) * 3,
            "fatigue_level": 3.0 + (index % 3) * 0.5,
        })
    return pd.DataFrame(rows)


def extreme_reading(astronaut_id="AST-ML", offset_days=31):
    return {
        "astronaut_id": astronaut_id,
        "recorded_at": START + timedelta(days=offset_days),
        "heart_rate": 190.0,
        "systolic_bp": 190.0,
        "diastolic_bp": 125.0,
        "body_temperature": 40.5,
        "oxygen_saturation": 80.0,
        "sleep_duration": 0.5,
        "physical_activity": 0.0,
        "fatigue_level": 10.0,
    }


def insert_frame(frame):
    HealthReading.objects.bulk_create([
        HealthReading(
            astronaut_id=row["astronaut_id"],
            recorded_at=row["recorded_at"],
            source="simulated",
            **{
                metric: float(row[metric])
                for metric in (
                    "heart_rate",
                    "systolic_bp",
                    "diastolic_bp",
                    "body_temperature",
                    "oxygen_saturation",
                    "sleep_duration",
                    "physical_activity",
                    "fatigue_level",
                )
            },
        )
        for row in frame.to_dict("records")
    ])


class AnomalyModelTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.model_dir = Path(self.temp_dir.name)

    def test_train_score_and_persist(self):
        frame = training_frame()

        artifact = train_personal_anomaly_model(
            "AST-ML",
            frame,
            n_estimators=50,
        )
        path = train_and_save_personal_anomaly_model(
            "AST-ML",
            frame,
            model_dir=self.model_dir,
            n_estimators=50,
        )[1]

        loaded = load_personal_anomaly_model(
            "AST-ML",
            model_dir=self.model_dir,
        )
        normal = score_reading(frame.iloc[-1].to_dict(), loaded)
        extreme = score_reading(extreme_reading(), loaded)

        self.assertTrue(path.exists())
        self.assertEqual(artifact["sample_count"], 30)
        self.assertEqual(loaded["astronaut_id"], "AST-ML")
        self.assertEqual(normal["status"], STATUS_NORMAL)
        self.assertFalse(normal["is_anomaly"])
        self.assertEqual(extreme["status"], STATUS_ANOMALY)
        self.assertTrue(extreme["is_anomaly"])
        self.assertGreater(
            extreme["anomaly_score"],
            normal["anomaly_score"],
        )
        self.assertGreater(
            extreme["top_deviating_metrics"][0]["absolute_z"],
            1.0,
        )

    def test_missing_metrics_are_imputed(self):
        frame = training_frame()
        artifact = train_personal_anomaly_model(
            "AST-ML",
            frame,
            n_estimators=50,
        )
        reading = {
            **extreme_reading(),
            "heart_rate": None,
            "sleep_duration": None,
        }

        result = score_reading(reading, artifact)

        self.assertTrue(result["evaluated"])
        self.assertEqual(
            set(result["missing_metrics"]),
            {"heart_rate", "sleep_duration"},
        )
        self.assertNotIn(
            "heart_rate",
            [item["metric"] for item in result["top_deviating_metrics"]],
        )

    def test_no_metrics_available_is_not_evaluated(self):
        artifact = train_personal_anomaly_model(
            "AST-ML",
            training_frame(),
            n_estimators=50,
        )
        reading = {
            "recorded_at": START + timedelta(days=31),
            "heart_rate": None,
            "systolic_bp": None,
            "diastolic_bp": None,
            "body_temperature": None,
            "oxygen_saturation": None,
            "sleep_duration": None,
            "physical_activity": None,
            "fatigue_level": None,
        }

        result = score_reading(reading, artifact)

        self.assertEqual(result["status"], STATUS_NOT_EVALUATED)
        self.assertFalse(result["evaluated"])

    def test_insufficient_training_data(self):
        with self.assertRaises(InsufficientTrainingData):
            train_personal_anomaly_model(
                "AST-ML",
                training_frame(days=10),
            )

    def test_invalid_training_parameters(self):
        with self.assertRaises(ValueError):
            train_personal_anomaly_model(
                "AST-ML",
                training_frame(),
                contamination=0,
            )
        with self.assertRaises(ValueError):
            train_personal_anomaly_model(
                "AST-ML",
                training_frame(),
                min_samples=4,
            )

    def test_missing_and_corrupt_models(self):
        missing = evaluate_personal_anomaly(
            "AST-ML",
            extreme_reading(),
            model_dir=self.model_dir,
        )

        path = model_path("AST-ML", self.model_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not a model")

        corrupt = evaluate_personal_anomaly(
            "AST-ML",
            extreme_reading(),
            model_dir=self.model_dir,
        )

        self.assertEqual(missing["status"], STATUS_NOT_TRAINED)
        self.assertEqual(corrupt["status"], STATUS_ERROR)

    def test_model_path_is_safe_and_unique(self):
        first = model_path("AST/../001", self.model_dir)
        second = model_path("AST-OTHER", self.model_dir)

        self.assertEqual(first.parent, self.model_dir)
        self.assertNotEqual(first, second)
        self.assertNotIn("..", first.name)


class AnomalyModelCommandTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.model_dir = Path(self.temp_dir.name)

    def test_command_trains_model(self):
        insert_frame(training_frame())
        output = StringIO()

        with override_settings(INTELLIGENCE_MODEL_DIR=self.model_dir):
            call_command(
                "train_anomaly_models",
                "--astronaut-id",
                "AST-ML",
                "--n-estimators",
                "50",
                stdout=output,
            )

        self.assertIn("Trained AST-ML", output.getvalue())
        self.assertTrue(
            model_path("AST-ML", self.model_dir).exists()
        )

    def test_command_skips_insufficient_data(self):
        insert_frame(training_frame(days=5))
        output = StringIO()
        errors = StringIO()

        with override_settings(INTELLIGENCE_MODEL_DIR=self.model_dir):
            call_command(
                "train_anomaly_models",
                "--astronaut-id",
                "AST-ML",
                "--n-estimators",
                "50",
                stdout=output,
                stderr=errors,
            )

        self.assertIn("Skipped AST-ML", errors.getvalue())
        self.assertFalse(
            model_path("AST-ML", self.model_dir).exists()
        )


class AnomalyModelIntegrationTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.model_dir = Path(self.temp_dir.name)

        frame = training_frame()
        insert_frame(frame)
        recalculate_baselines("AST-ML")

        with override_settings(INTELLIGENCE_MODEL_DIR=self.model_dir):
            train_and_save_personal_anomaly_model(
                "AST-ML",
                frame,
                model_dir=self.model_dir,
                n_estimators=50,
            )

        values = extreme_reading()
        self.current = HealthReading.objects.create(
            astronaut_id="AST-ML",
            recorded_at=values["recorded_at"],
            source="external",
            **{
                key: value
                for key, value in values.items()
                if key not in {"astronaut_id", "recorded_at"}
            },
        )

    def test_statistical_analysis_includes_ml_score(self):
        with override_settings(INTELLIGENCE_MODEL_DIR=self.model_dir):
            result = analyze_statistics("AST-ML")

        self.assertEqual(result["ml_anomaly"]["status"], STATUS_ANOMALY)
        self.assertTrue(result["ml_anomaly"]["is_anomaly"])
        self.assertTrue(result["summary"]["requires_review"])
        self.assertFalse(result["ml_anomaly"]["in_sample"])

    def test_disabling_ml(self):
        with override_settings(INTELLIGENCE_MODEL_DIR=self.model_dir):
            result = analyze_statistics("AST-ML", include_ml=False)

        self.assertEqual(result["ml_anomaly"]["status"], "DISABLED")

    def test_in_sample_warning(self):
        training_reading = HealthReading.objects.filter(
            astronaut_id="AST-ML"
        ).order_by("recorded_at").first()

        with override_settings(INTELLIGENCE_MODEL_DIR=self.model_dir):
            result = analyze_statistics(
                "AST-ML",
                reading=training_reading,
            )

        self.assertTrue(result["ml_anomaly"]["in_sample"])
        self.assertIn(
            "in-sample",
            " ".join(result["warnings"]),
        )
