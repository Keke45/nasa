import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from baselines.models import HealthReading
from baselines.service import recalculate_baselines
from ml.metrics import METRIC_COLUMNS
from ml.trend_prediction import (
    TREND_DECREASING,
    TREND_INCREASING,
    TREND_INSUFFICIENT,
    TREND_STABLE,
    predict_trend,
)
from services.anomaly_service import (
    SEVERITY_ANOMALY,
    SEVERITY_NORMAL,
    SEVERITY_NOT_EVALUATED,
    SEVERITY_SEVERE,
    SEVERITY_WATCH,
    AnomalyRules,
    evaluate_metric_anomaly,
    evaluate_reading_anomalies,
    summarize_anomalies,
)
from services.comparison_service import (
    DIRECTION_ABOVE,
    DIRECTION_AT,
    STATUS_EVALUATED,
    STATUS_INSUFFICIENT_BASELINE,
    STATUS_MISSING_CURRENT,
    STATUS_NO_BASELINE,
    compare_metric,
    compare_reading,
    summarize_comparisons,
)
from services.constants import BASELINE_KIND_RECENT
from services.statistical_service import analyze_statistics

START = timezone.now().replace(
    hour=7, minute=0, second=0, microsecond=0
) - timedelta(days=40)


def baseline(**overrides):
    values = {
        "metric": "heart_rate",
        "baseline_value": 70.0,
        "median_value": 70.0,
        "std_dev": 5.0,
        "min_value": 60.0,
        "max_value": 80.0,
        "rolling_average": 70.0,
        "rolling_window_days": 7,
        "rolling_sample_count": 7,
        "sample_count": 20,
        "window_days": 30,
        "baseline_kind": "RECENT",
        "baseline_status": "ESTABLISHED",
        "baseline_version": 2,
        "snapshot_id": 11,
        "is_usable": True,
    }
    values.update(overrides)
    return values


def reading_values(heart_rate=70.0):
    return {
        "heart_rate": heart_rate,
        "systolic_bp": 115.0,
        "diastolic_bp": 75.0,
        "body_temperature": 36.6,
        "oxygen_saturation": 98.0,
        "sleep_duration": 7.5,
        "physical_activity": 60.0,
        "fatigue_level": 3.0,
    }


def create_reading(astronaut_id, offset_days, **overrides):
    values = reading_values()
    values.update(overrides)
    return HealthReading.objects.create(
        astronaut_id=astronaut_id,
        recorded_at=START + timedelta(days=offset_days),
        source="external",
        **values,
    )


def seed_baseline_history(astronaut_id, days=20):
    return [
        create_reading(astronaut_id, index, heart_rate=60 + index)
        for index in range(days)
    ]


def trend_points(values, start=START):
    return [
        {
            "recorded_at": start + timedelta(days=index),
            "heart_rate": value,
        }
        for index, value in enumerate(values)
    ]


class ComparisonServiceTests(TestCase):
    def test_value_above_baseline(self):
        result = compare_metric("heart_rate", 80.0, baseline())

        self.assertEqual(result["status"], STATUS_EVALUATED)
        self.assertTrue(result["evaluated"])
        self.assertEqual(result["direction"], DIRECTION_ABOVE)
        self.assertAlmostEqual(result["difference"], 10.0)
        self.assertAlmostEqual(result["percentage_change"], 100 / 70 * 10)
        self.assertAlmostEqual(result["z_score"], 2.0)
        self.assertAlmostEqual(result["absolute_z"], 2.0)
        self.assertFalse(result["outside_observed_range"])
        self.assertAlmostEqual(result["distance_outside_range"], 0.0)
        self.assertAlmostEqual(result["range_position"], 1.0)

    def test_value_at_baseline_and_exactly_on_range_boundary(self):
        at_baseline = compare_metric("heart_rate", 70.0, baseline())
        at_max = compare_metric("heart_rate", 80.0, baseline())

        self.assertEqual(at_baseline["direction"], DIRECTION_AT)
        self.assertAlmostEqual(at_baseline["z_score"], 0.0)
        self.assertFalse(at_max["outside_observed_range"])

    def test_value_outside_personal_range(self):
        result = compare_metric("heart_rate", 85.0, baseline())

        self.assertTrue(result["outside_observed_range"])
        self.assertAlmostEqual(result["distance_outside_range"], 5.0)
        self.assertAlmostEqual(result["range_position"], 1.25)

    def test_zero_baseline_has_no_percentage_change(self):
        result = compare_metric(
            "physical_activity",
            10.0,
            baseline(
                metric="physical_activity",
                baseline_value=0.0,
                min_value=0.0,
                max_value=5.0,
                std_dev=1.0,
            ),
        )

        self.assertIsNone(result["percentage_change"])
        self.assertEqual(result["direction"], DIRECTION_ABOVE)

    def test_missing_baseline_and_current_value(self):
        no_baseline = compare_metric("heart_rate", 70.0, None)
        missing_current = compare_metric("heart_rate", None, baseline())

        self.assertEqual(no_baseline["status"], STATUS_NO_BASELINE)
        self.assertEqual(no_baseline["direction"], "UNKNOWN")
        self.assertFalse(no_baseline["evaluated"])
        self.assertEqual(
            missing_current["status"], STATUS_MISSING_CURRENT
        )
        self.assertFalse(missing_current["evaluated"])

    def test_insufficient_baseline_is_not_evaluated(self):
        result = compare_metric(
            "heart_rate",
            80.0,
            baseline(baseline_status="INSUFFICIENT", is_usable=None),
        )

        self.assertEqual(result["status"], STATUS_INSUFFICIENT_BASELINE)
        self.assertFalse(result["evaluated"])
        self.assertIn("insufficient", result["summary"])

    def test_no_std_dev_means_no_z_score(self):
        result = compare_metric(
            "heart_rate",
            80.0,
            baseline(std_dev=None),
        )

        self.assertAlmostEqual(result["difference"], 10.0)
        self.assertIsNone(result["z_score"])
        self.assertIsNone(result["absolute_z"])
        self.assertIn("no Z-score", result["summary"])

    def test_compare_reading_and_summary(self):
        baselines = {
            "heart_rate": baseline(),
            "oxygen_saturation": baseline(
                metric="oxygen_saturation",
                baseline_value=98.0,
                std_dev=1.0,
                min_value=96.0,
                max_value=100.0,
            ),
        }

        comparisons = compare_reading(reading_values(heart_rate=85.0), baselines)
        summary = summarize_comparisons(comparisons)

        self.assertEqual(len(comparisons), len(METRIC_COLUMNS))
        self.assertEqual(comparisons[0]["metric"], "heart_rate")
        self.assertEqual(summary["evaluated"], 2)
        self.assertEqual(summary["outside_observed_range"], ["heart_rate"])
        self.assertEqual(
            summary["strongest_deviation"]["metric"], "heart_rate"
        )
        self.assertEqual(summary["deviations_over_2sd"], ["heart_rate"])


class AnomalyServiceTests(TestCase):
    def test_severity_thresholds(self):
        cases = {
            115.0: SEVERITY_NORMAL,
            125.0: SEVERITY_WATCH,
            135.0: SEVERITY_ANOMALY,
            145.0: SEVERITY_SEVERE,
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                result = evaluate_metric_anomaly(
                    "heart_rate",
                    value,
                    baseline(baseline_value=100.0, std_dev=10.0),
                )
                self.assertEqual(result["severity"], expected)
                self.assertTrue(result["evaluated"])

    def test_not_evaluated_without_baseline_or_current(self):
        no_baseline = evaluate_metric_anomaly("heart_rate", 100.0, None)
        no_current = evaluate_metric_anomaly("heart_rate", None, baseline())

        for result in (no_baseline, no_current):
            self.assertEqual(
                result["severity"], SEVERITY_NOT_EVALUATED
            )
            self.assertFalse(result["evaluated"])
            self.assertFalse(result["requires_review"])

    def test_insufficient_baseline_is_not_evaluated(self):
        result = evaluate_metric_anomaly(
            "heart_rate",
            145.0,
            baseline(baseline_status="INSUFFICIENT", is_usable=False),
        )

        self.assertEqual(result["severity"], SEVERITY_NOT_EVALUATED)
        self.assertIn("insufficient", result["reason"])

    def test_recent_moving_average_can_escalate_severity(self):
        result = evaluate_metric_anomaly(
            "heart_rate",
            105.0,
            baseline(baseline_value=100.0, std_dev=10.0),
            recent_values=[130.0] * 5,
        )

        self.assertEqual(result["severity"], SEVERITY_ANOMALY)
        self.assertAlmostEqual(result["moving_average"], 130.0)
        self.assertAlmostEqual(result["moving_average_z"], 3.0)
        self.assertEqual(
            result["moving_average_severity"], SEVERITY_ANOMALY
        )

    def test_moving_average_does_not_evaluate_missing_current(self):
        result = evaluate_metric_anomaly(
            "heart_rate",
            None,
            baseline(std_dev=10.0),
            recent_values=[130.0] * 5,
        )

        self.assertEqual(result["severity"], SEVERITY_NOT_EVALUATED)

    def test_invalid_rules(self):
        with self.assertRaises(ValueError):
            AnomalyRules(watch_z=3.0, anomaly_z=2.0)
        with self.assertRaises(ValueError):
            AnomalyRules(moving_average_z=0)

    def test_summary(self):
        anomalies = [
            evaluate_metric_anomaly(
                "heart_rate", 145.0, baseline(std_dev=10.0)
            ),
            evaluate_metric_anomaly(
                "heart_rate", 70.0, baseline(metric="oxygen_saturation")
            ),
            evaluate_metric_anomaly("fatigue_level", 5.0, None),
        ]

        summary = summarize_anomalies(anomalies)

        self.assertEqual(summary["highest_severity"], SEVERITY_SEVERE)
        self.assertEqual(summary["alert_count"], 1)
        self.assertEqual(summary["counts"][SEVERITY_SEVERE], 1)
        self.assertEqual(
            summary["counts"][SEVERITY_NOT_EVALUATED], 1
        )


class TrendPredictionTests(TestCase):
    def test_increasing_trend_uses_days(self):
        result = predict_trend(
            trend_points(range(60, 80)),
            "heart_rate",
        )

        self.assertEqual(result["direction"], TREND_INCREASING)
        self.assertAlmostEqual(result["slope_per_day"], 1.0)
        self.assertAlmostEqual(result["slope_per_week"], 7.0)
        self.assertAlmostEqual(result["r_squared"], 1.0)
        self.assertAlmostEqual(result["projected_change"], 7.0)
        self.assertAlmostEqual(result["projected_value"], 86.0)
        self.assertTrue(result["reliable"])

    def test_decreasing_trend(self):
        result = predict_trend(
            trend_points(range(100, 80, -1)),
            "heart_rate",
        )

        self.assertEqual(result["direction"], TREND_DECREASING)
        self.assertAlmostEqual(result["slope_per_day"], -1.0)

    def test_stable_values(self):
        result = predict_trend(
            trend_points([70.0] * 10),
            "heart_rate",
        )

        self.assertEqual(result["direction"], TREND_STABLE)
        self.assertAlmostEqual(result["slope_per_day"], 0.0)
        self.assertAlmostEqual(result["r_squared"], 1.0)

    def test_gap_is_measured_in_calendar_days(self):
        points = [
            {"recorded_at": START, "heart_rate": 60.0},
            {"recorded_at": START + timedelta(days=10), "heart_rate": 70.0},
        ]

        result = predict_trend(points, "heart_rate", min_samples=2)

        self.assertAlmostEqual(result["slope_per_day"], 1.0)
        self.assertAlmostEqual(result["trend_duration_days"], 10.0)

    def test_insufficient_samples(self):
        result = predict_trend(
            trend_points([60.0, 61.0]),
            "heart_rate",
        )

        self.assertEqual(result["direction"], TREND_INSUFFICIENT)
        self.assertEqual(result["sample_count"], 2)
        self.assertIsNone(result["slope_per_day"])

    def test_calendar_moving_averages(self):
        result = predict_trend(
            trend_points(range(60, 80)),
            "heart_rate",
            short_window_days=7,
            long_window_days=30,
        )

        self.assertAlmostEqual(result["short_moving_average"], 75.5)
        self.assertAlmostEqual(result["long_moving_average"], 69.5)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            predict_trend([], "unknown_metric")
        with self.assertRaises(ValueError):
            predict_trend([], "heart_rate", short_window_days=31)
        with self.assertRaises(ValueError):
            predict_trend([], "heart_rate", min_samples=1)


class StatisticalServiceTests(TestCase):
    def test_analysis_combines_comparisons_anomalies_and_trends(self):
        seed_baseline_history("AST-STAT", days=20)
        recalculate_baselines("AST-STAT")
        current = create_reading("AST-STAT", 20, heart_rate=100.0)

        result = analyze_statistics("AST-STAT")

        self.assertEqual(result["astronaut_id"], "AST-STAT")
        self.assertEqual(result["reading"]["id"], current.id)
        self.assertEqual(
            result["baseline"]["kind"], BASELINE_KIND_RECENT
        )
        self.assertEqual(result["baseline"]["usable_count"], 8)
        self.assertEqual(len(result["comparisons"]), len(METRIC_COLUMNS))
        self.assertEqual(len(result["anomalies"]), len(METRIC_COLUMNS))
        self.assertEqual(len(result["trends"]), len(METRIC_COLUMNS))

        heart_rate = next(
            item
            for item in result["comparisons"]
            if item["metric"] == "heart_rate"
        )
        self.assertEqual(heart_rate["status"], STATUS_EVALUATED)
        self.assertTrue(heart_rate["outside_observed_range"])

        anomaly = next(
            item
            for item in result["anomalies"]
            if item["metric"] == "heart_rate"
        )
        self.assertEqual(anomaly["severity"], SEVERITY_SEVERE)
        self.assertTrue(result["summary"]["requires_review"])

        trend = result["trends"]["heart_rate"]
        self.assertEqual(trend["direction"], TREND_INCREASING)
        self.assertEqual(trend["sample_count"], 21)

        json.dumps(result)

    def test_analysis_without_baselines_still_returns_trends(self):
        create_reading("AST-NOBASE", 0)

        result = analyze_statistics("AST-NOBASE")

        self.assertEqual(result["baseline"]["metric_count"], 0)
        self.assertTrue(
            all(
                comparison["status"] == STATUS_NO_BASELINE
                for comparison in result["comparisons"]
            )
        )
        self.assertIn(
            "No current baselines",
            " ".join(result["warnings"]),
        )

    def test_insufficient_baseline_is_reported(self):
        for index in range(3):
            create_reading("AST-FEW", index)
        recalculate_baselines("AST-FEW")
        create_reading("AST-FEW", 3)

        result = analyze_statistics("AST-FEW")

        self.assertEqual(result["baseline"]["usable_count"], 0)
        self.assertTrue(
            all(
                anomaly["severity"] == SEVERITY_NOT_EVALUATED
                for anomaly in result["anomalies"]
            )
        )
        self.assertIn("Insufficient baseline data", " ".join(
            result["warnings"]
        ))

    def test_as_of_selects_earlier_reading(self):
        first = create_reading("AST-ASOF", 0, heart_rate=70.0)
        create_reading("AST-ASOF", 1, heart_rate=90.0)

        result = analyze_statistics(
            "AST-ASOF",
            as_of=first.recorded_at,
        )

        self.assertEqual(result["reading"]["id"], first.id)

    def test_reading_id_and_astronaut_validation(self):
        reading = create_reading("AST-ID", 0)

        result = analyze_statistics("AST-ID", reading_id=reading.id)

        self.assertEqual(result["reading"]["id"], reading.id)

        with self.assertRaises(ValueError):
            analyze_statistics("AST-ID", reading=reading, reading_id=reading.id)

        with self.assertRaises(ValueError):
            analyze_statistics("AST-OTHER", reading=reading)

    def test_missing_reading(self):
        with self.assertRaises(HealthReading.DoesNotExist):
            analyze_statistics("AST-NONE")

        with self.assertRaises(HealthReading.DoesNotExist):
            analyze_statistics("AST-NONE", reading_id=999999)

    def test_baseline_overlap_warning(self):
        create_reading("AST-OVERLAP", 0)
        recalculate_baselines("AST-OVERLAP")
        result = analyze_statistics("AST-OVERLAP")

        self.assertIn("not strictly as-of clean", " ".join(
            result["warnings"]
        ))

    def test_argument_validation(self):
        create_reading("AST-VALID", 0)

        with self.assertRaises(ValueError):
            analyze_statistics("AST-VALID", baseline_kind="UNKNOWN")
        with self.assertRaises(ValueError):
            analyze_statistics("AST-VALID", lookback_days=0)
        with self.assertRaises(ValueError):
            analyze_statistics(
                "AST-VALID",
                lookback_days=10,
                long_window_days=30,
            )
