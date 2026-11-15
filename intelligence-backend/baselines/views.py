"""REST API for reading ingestion and personal baselines."""

import logging
import secrets

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Min
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from baselines.models import HealthReading
from baselines.serializers import (
    BaselineSnapshotSerializer,
    CalculateBaselineSerializer,
    HealthBaselineSerializer,
    HealthReadingSerializer,
    RegistrationIntakeSerializer,
    StatisticalAnalysisQuerySerializer,
)
from baselines.service import (
    get_baseline_history,
    get_current_baselines,
    get_current_snapshot,
    get_snapshot_history,
    recalculate_baselines,
    store_registration_reading,
)
from ml.metrics import METRIC_COLUMNS
from services.constants import (
    BASELINE_KIND_CHOICES,
    DEFAULT_RECENT_WINDOW_DAYS,
    MIN_SAMPLES_INSUFFICIENT,
    STATUS_INSUFFICIENT,
)
from services.statistical_service import analyze_statistics

logger = logging.getLogger(__name__)

DASHBOARD_SEVERITIES = [
    "SEVERE",
    "ANOMALY",
    "WATCH",
    "NORMAL",
    "NOT_EVALUATED",
]
DASHBOARD_SEVERITY_RANK = {
    severity: len(DASHBOARD_SEVERITIES) - index
    for index, severity in enumerate(DASHBOARD_SEVERITIES)
}


class PublicAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


def _ingest_token_valid(request):
    configured_token = getattr(
        settings, "INTELLIGENCE_INGEST_TOKEN", ""
    )
    provided_token = request.headers.get("X-Ingest-Token", "")

    if not configured_token:
        return True

    return secrets.compare_digest(configured_token, provided_token)


def _valid_kind(value):
    if value is None:
        return None, None

    kind = str(value).upper()
    allowed = {choice[0] for choice in BASELINE_KIND_CHOICES}
    if kind not in allowed:
        return None, f"kind must be one of: {', '.join(sorted(allowed))}"

    return kind, None


def _parse_window(value):
    if value is None or value == "":
        return DEFAULT_RECENT_WINDOW_DAYS, None
    if str(value).lower() in {"all", "none", "null"}:
        return None, None
    try:
        window = int(value)
    except (TypeError, ValueError):
        return None, "window_days must be an integer or 'all'"
    if window < 1:
        return None, "window_days must be at least 1"
    return window, None


def _warnings(astronaut_id, snapshot, baselines):
    messages = []

    sources = set(
        HealthReading.objects
        .filter(astronaut_id=str(astronaut_id))
        .values_list("source", flat=True)
        .distinct()
    )
    if "simulated" in sources:
        messages.append(
            "Baselines are computed from simulated data and are not "
            "for clinical use."
        )

    if snapshot is not None and snapshot.reading_count == 0:
        messages.append(
            "No readings were available for this calculation."
        )

    insufficient = [
        baseline.metric
        for baseline in baselines
        if baseline.baseline_status == STATUS_INSUFFICIENT
    ]
    if insufficient:
        messages.append(
            "Insufficient data for: "
            + ", ".join(sorted(insufficient))
            + ". These baselines must not be used for comparison."
        )

    return messages


def _baseline_payload(astronaut_id, baselines, snapshot):
    return {
        "astronaut_id": str(astronaut_id),
        "snapshot": (
            BaselineSnapshotSerializer(snapshot).data
            if snapshot is not None else None
        ),
        "baselines": HealthBaselineSerializer(
            baselines, many=True
        ).data,
        "warnings": _warnings(astronaut_id, snapshot, baselines),
    }


class BaselineListView(PublicAPIView):
    def get(self, request, astronaut_id):
        kind, error = _valid_kind(
            request.query_params.get("kind")
            or request.query_params.get("baseline_kind")
        )
        if error:
            return Response(
                {"detail": error}, status=status.HTTP_400_BAD_REQUEST
            )

        metric = request.query_params.get("metric")
        if metric is not None and metric not in METRIC_COLUMNS:
            return Response(
                {"detail": "Unknown metric"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        baselines = list(get_current_baselines(
            astronaut_id,
            metric=metric,
            kind=kind,
        ))
        snapshot = get_current_snapshot(astronaut_id)

        return Response(_baseline_payload(
            astronaut_id, baselines, snapshot
        ))


class BaselineCalculateView(PublicAPIView):
    def post(self, request, astronaut_id):
        if not isinstance(request.data, dict):
            return Response(
                {"detail": "Request body must be a JSON object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = dict(request.data)

        if isinstance(payload.get("window_days"), str) and (
            payload["window_days"].strip().lower() == "all"
        ):
            payload["window_days"] = None

        serializer = CalculateBaselineSerializer(data=payload)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            baselines = recalculate_baselines(
                astronaut_id,
                window_days=data["window_days"],
                rolling_window_days=data["rolling_window_days"],
                before=data.get("before"),
            )
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        snapshot = baselines[0].snapshot if baselines else None
        payload = _baseline_payload(astronaut_id, baselines, snapshot)
        payload["created"] = len(baselines)

        return Response(payload, status=status.HTTP_201_CREATED)


class BaselineHistoryView(PublicAPIView):
    def get(self, request, astronaut_id):
        kind, error = _valid_kind(
            request.query_params.get("kind")
            or request.query_params.get("baseline_kind")
        )
        if error:
            return Response(
                {"detail": error}, status=status.HTTP_400_BAD_REQUEST
            )

        metric = request.query_params.get("metric")
        if metric is not None and metric not in METRIC_COLUMNS:
            return Response(
                {"detail": "Unknown metric"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_window = request.query_params.get("window_days")
        filter_window = raw_window is not None
        window_days = None

        if filter_window:
            window_days, error = _parse_window(raw_window)
            if error:
                return Response(
                    {"detail": error},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            return Response(
                {"detail": "limit must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = max(1, min(limit, 100))

        snapshots = list(get_snapshot_history(astronaut_id, limit=limit))
        snapshot_ids = [snapshot.id for snapshot in snapshots]

        baselines = get_baseline_history(
            astronaut_id,
            metric=metric,
            kind=kind,
            window_days=window_days,
            filter_window=filter_window,
        ).filter(snapshot_id__in=snapshot_ids)

        grouped = {}
        for baseline in baselines:
            grouped.setdefault(baseline.snapshot_id, []).append(baseline)

        history = [
            {
                "snapshot": BaselineSnapshotSerializer(snapshot).data,
                "baselines": HealthBaselineSerializer(
                    grouped.get(snapshot.id, []), many=True
                ).data,
            }
            for snapshot in snapshots
        ]

        return Response({
            "astronaut_id": str(astronaut_id),
            "history": history,
        })


class ReadingIngestView(PublicAPIView):
    def post(self, request):
        if not _ingest_token_valid(request):
            return Response(
                {"detail": "Invalid or missing ingest token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        payload = request.data

        if isinstance(payload, dict) and "readings" in payload:
            items = payload["readings"]
        elif isinstance(payload, list):
            items = payload
        else:
            items = [payload]

        if not isinstance(items, list) or not items:
            return Response(
                {"detail": "At least one reading is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(items) > 1000:
            return Response(
                {"detail": "A batch may contain at most 1000 readings"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = []
        errors = []

        for index, item in enumerate(items):
            serializer = HealthReadingSerializer(data=item)
            if serializer.is_valid():
                validated.append(serializer.validated_data)
            else:
                errors.append({
                    "index": index,
                    "errors": serializer.errors,
                })

        if errors:
            return Response(
                {"detail": "Validation failed", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = 0
        updated = 0

        with transaction.atomic():
            for data in validated:
                defaults = {
                    metric: data[metric]
                    for metric in METRIC_COLUMNS
                    if metric in data
                }
                defaults["source"] = data.get("source", "external")

                _, was_created = HealthReading.objects.update_or_create(
                    astronaut_id=data["astronaut_id"],
                    recorded_at=data["recorded_at"],
                    defaults=defaults,
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        return Response({
            "created": created,
            "updated": updated,
            "total": len(validated),
        }, status=status.HTTP_201_CREATED)


class RegistrationIntakeView(PublicAPIView):
    def post(self, request):
        if not _ingest_token_valid(request):
            return Response(
                {"detail": "Invalid or missing ingest token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = RegistrationIntakeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        astronaut_id = data["personal"]["astronaut_id"]
        metrics = data["health"]["mapped_metrics"]

        reading, created = store_registration_reading(
            astronaut_id,
            metrics,
            recorded_at=data.get("recorded_at"),
        )

        readings_available = HealthReading.objects.filter(
            astronaut_id=astronaut_id
        ).count()
        missing_metrics = [
            metric for metric in METRIC_COLUMNS if metric not in metrics
        ]
        warnings = []

        if readings_available < MIN_SAMPLES_INSUFFICIENT:
            warnings.append(
                f"Only {readings_available} reading(s) are available. "
                f"Personal baselines need at least "
                f"{MIN_SAMPLES_INSUFFICIENT}."
            )
        warnings.append(
            "Registration data was stored but baselines were not "
            "recalculated."
        )

        response_data = {
            "astronaut_id": astronaut_id,
            "created": created,
            "reading": HealthReadingSerializer(reading).data,
            "baseline": {
                "readings_available": readings_available,
                "minimum_for_provisional": MIN_SAMPLES_INSUFFICIENT,
                "calculation_required": True,
            },
            "missing_metrics": missing_metrics,
            "warnings": warnings,
        }

        return Response(
            response_data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class ReadingListView(PublicAPIView):
    def get(self, request, astronaut_id):
        queryset = HealthReading.objects.filter(
            astronaut_id=str(astronaut_id)
        ).order_by("recorded_at")

        date_field = serializers.DateTimeField()

        for name in ("start", "end"):
            raw = request.query_params.get(name)
            if raw is None:
                continue

            try:
                value = date_field.to_internal_value(raw)
            except serializers.ValidationError:
                return Response(
                    {"detail": f"Invalid {name} timestamp"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if name == "start":
                queryset = queryset.filter(recorded_at__gte=value)
            else:
                queryset = queryset.filter(recorded_at__lte=value)

        try:
            limit = int(request.query_params.get("limit", 500))
        except (TypeError, ValueError):
            return Response(
                {"detail": "limit must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = max(1, min(limit, 5000))

        readings = list(queryset[:limit])

        return Response({
            "astronaut_id": str(astronaut_id),
            "count": len(readings),
            "readings": HealthReadingSerializer(
                readings, many=True
            ).data,
        })


class StatisticalAnalysisView(PublicAPIView):
    def get(self, request, astronaut_id):
        serializer = StatisticalAnalysisQuerySerializer(
            data=request.query_params
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            result = analyze_statistics(
                astronaut_id,
                reading_id=data.get("reading_id"),
                as_of=data.get("as_of"),
                baseline_kind=data["baseline_kind"],
                lookback_days=data["lookback_days"],
                rolling_window_days=data["rolling_window_days"],
                short_window_days=data["short_window_days"],
                long_window_days=data["long_window_days"],
                anomaly_rules=data["anomaly_rules"],
                include_ml=data["include_ml"],
            )
        except HealthReading.DoesNotExist as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)


def _iso(value):
    return value.isoformat() if value is not None else None


def _dashboard_reading_payload(reading):
    if reading is None:
        return None

    return {
        "id": reading.id,
        "recorded_at": _iso(reading.recorded_at),
        "source": reading.source,
        "values": {
            metric: getattr(reading, metric)
            for metric in METRIC_COLUMNS
        },
    }


def _compact_alert(item, astronaut_id, recorded_at, baseline_version):
    return {
        "astronaut_id": str(astronaut_id),
        "recorded_at": recorded_at,
        "metric": item.get("metric"),
        "metric_label": item.get("metric_label") or item.get("metric"),
        "unit": item.get("unit") or "",
        "severity": item.get("severity"),
        "current_value": item.get("current_value"),
        "baseline_value": item.get("baseline_value"),
        "z_score": item.get("z_score"),
        "direction": item.get("direction"),
        "difference": item.get("difference"),
        "baseline_status": item.get("baseline_status"),
        "baseline_version": (
            item.get("baseline_version") or baseline_version
        ),
        "outside_observed_range": bool(
            item.get("outside_observed_range")
        ),
        "reason": item.get("reason") or "",
    }


def _alert_observation(alert):
    if alert["reason"]:
        return alert["reason"]

    label = alert["metric_label"] or alert["metric"] or "Measurement"
    direction = alert["direction"]
    difference = alert["difference"]
    unit = alert["unit"]

    if difference is not None and direction in {"ABOVE", "BELOW"}:
        amount = f"{abs(float(difference)):.1f}"
        measure = f"{amount} {unit}" if unit else amount
        return (
            f"{label} is {measure} {direction.lower()} the "
            "personal baseline."
        )

    return f"{label} deviates from the personal baseline."


def _contributing_factors(alert, alerts, trends):
    factors = []

    for other in alerts:
        if other["metric"] == alert["metric"]:
            continue
        direction = (other.get("direction") or "").lower()
        label = other.get("metric_label") or other.get("metric")
        factors.append(
            f"{label} {direction} baseline".strip()
        )

    for trend in trends.values():
        direction = trend.get("direction")
        if direction in {None, "STABLE"}:
            continue
        factors.append(
            f"{trend.get('metric_label')} trending "
            f"{str(direction).lower()}"
        )

    unique = []
    for factor in factors:
        if factor not in unique:
            unique.append(factor)

    return unique[:4]


def _dashboard_entry(stats):
    astronaut_id = stats["astronaut_id"]
    latest_payload = None
    analysis = None
    error_message = None

    try:
        analysis = analyze_statistics(astronaut_id)
    except Exception as error:
        logger.exception(
            "Mission overview analysis failed for %s", astronaut_id
        )
        error_message = str(error)
        latest = (
            HealthReading.objects
            .filter(astronaut_id=astronaut_id)
            .order_by("-recorded_at")
            .first()
        )
        latest_payload = _dashboard_reading_payload(latest)

    if analysis is not None:
        latest_payload = analysis.get("reading")
        summary = analysis.get("summary") or {}
        anomaly_summary = summary.get("anomaly") or {}
        ml_summary = summary.get("ml_anomaly") or {}
        baseline = analysis.get("baseline") or {}
        recorded_at = (latest_payload or {}).get("recorded_at")
        baseline_version = baseline.get("version")

        alerts = [
            _compact_alert(
                item, astronaut_id, recorded_at, baseline_version
            )
            for item in (analysis.get("anomalies") or [])
            if item.get("evaluated")
            and item.get("severity")
            not in {None, "NORMAL", "NOT_EVALUATED"}
        ]

        trends = {
            metric: {
                "metric": metric,
                "metric_label": trend.get("metric_label") or metric,
                "unit": trend.get("unit") or "",
                "direction": trend.get("direction"),
                "slope_per_week": trend.get("slope_per_week"),
                "reliable": trend.get("reliable"),
            }
            for metric, trend in (analysis.get("trends") or {}).items()
        }

        severity = anomaly_summary.get("highest_severity")
        severity = severity or "NOT_EVALUATED"

        return {
            "astronaut_id": str(astronaut_id),
            "reading_count": stats["reading_count"],
            "first_reading_at": _iso(stats["first_reading_at"]),
            "last_reading_at": _iso(stats["last_reading_at"]),
            "latest_reading": latest_payload,
            "baseline": {
                "snapshot_id": baseline.get("snapshot_id"),
                "version": baseline_version,
                "kind": baseline.get("kind"),
                "window_days": baseline.get("window_days"),
                "usable_count": baseline.get("usable_count"),
                "metric_count": baseline.get("metric_count"),
            },
            "severity": severity,
            "alert_count": anomaly_summary.get("alert_count", 0),
            "requires_review": bool(
                summary.get("requires_review")
            ),
            "ml_status": ml_summary.get("status", "NOT_EVALUATED"),
            "ml_anomaly": ml_summary,
            "trend_directions": (
                summary.get("trend_directions") or {}
            ),
            "trends": trends,
            "alerts": alerts,
            "warnings": analysis.get("warnings") or [],
            "generated_at": analysis.get("generated_at"),
            "error": None,
        }

    return {
        "astronaut_id": str(astronaut_id),
        "reading_count": stats["reading_count"],
        "first_reading_at": _iso(stats["first_reading_at"]),
        "last_reading_at": _iso(stats["last_reading_at"]),
        "latest_reading": latest_payload,
        "baseline": {
            "snapshot_id": None,
            "version": None,
            "kind": None,
            "window_days": None,
            "usable_count": 0,
            "metric_count": 0,
        },
        "severity": "NOT_EVALUATED",
        "alert_count": 0,
        "requires_review": False,
        "ml_status": "NOT_EVALUATED",
        "ml_anomaly": {},
        "trend_directions": {},
        "trends": {},
        "alerts": [],
        "warnings": [],
        "generated_at": None,
        "error": error_message,
    }


def _build_mission_overview():
    stats_rows = list(
        HealthReading.objects
        .values("astronaut_id")
        .annotate(
            reading_count=Count("id"),
            first_reading_at=Min("recorded_at"),
            last_reading_at=Max("recorded_at"),
        )
        .order_by("astronaut_id")
    )

    astronauts = [_dashboard_entry(stats) for stats in stats_rows]

    alerts = []
    for entry in astronauts:
        for alert in entry["alerts"]:
            alert["observation"] = _alert_observation(alert)
            alert["contributing_factors"] = _contributing_factors(
                alert, entry["alerts"], entry["trends"]
            )
            alert["status"] = "NEW"
            alert["recommended_actions"] = []
            alerts.append(alert)

    alerts.sort(
        key=lambda item: item.get("recorded_at") or "",
        reverse=True,
    )
    alerts.sort(
        key=lambda item: DASHBOARD_SEVERITY_RANK.get(
            item.get("severity"), 0
        ),
        reverse=True,
    )

    severity_counts = {
        severity: 0 for severity in DASHBOARD_SEVERITIES
    }
    for entry in astronauts:
        severity = entry["severity"]
        if severity not in severity_counts:
            severity = "NOT_EVALUATED"
        severity_counts[severity] += 1

    last_reading_at = max(
        (
            entry["last_reading_at"]
            for entry in astronauts
            if entry["last_reading_at"]
        ),
        default=None,
    )

    return {
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "total_astronauts": len(astronauts),
            "monitored": len(astronauts),
            "active_alerts": sum(
                entry["alert_count"] for entry in astronauts
            ),
            "requiring_attention": sum(
                1
                for entry in astronauts
                if entry["requires_review"]
            ),
            "severity_counts": severity_counts,
            "last_reading_at": last_reading_at,
        },
        "astronauts": astronauts,
        "alerts": alerts,
    }


class MissionOverviewView(PublicAPIView):
    def get(self, request):
        return Response(_build_mission_overview())


class MissionAlertsView(PublicAPIView):
    def get(self, request):
        overview = _build_mission_overview()
        alerts = overview["alerts"]

        summary = {
            "total": len(alerts),
            "severe": sum(
                1 for alert in alerts
                if alert["severity"] == "SEVERE"
            ),
            "anomaly": sum(
                1 for alert in alerts
                if alert["severity"] == "ANOMALY"
            ),
            "watch": sum(
                1 for alert in alerts
                if alert["severity"] == "WATCH"
            ),
            "astronauts_affected": len({
                alert["astronaut_id"] for alert in alerts
            }),
            "requiring_attention": sum(
                1 for alert in alerts
                if alert["severity"] in {"SEVERE", "ANOMALY"}
            ),
        }

        return Response({
            "generated_at": overview["generated_at"],
            "summary": summary,
            "alerts": alerts,
        })
