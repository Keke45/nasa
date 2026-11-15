from django.urls import path

from . import views

urlpatterns = [
    path(
        "readings",
        views.ReadingIngestView.as_view(),
        name="reading-ingest",
    ),
    path(
        "registrations",
        views.RegistrationIntakeView.as_view(),
        name="registration-intake",
    ),
    path(
        "mission/overview",
        views.MissionOverviewView.as_view(),
        name="mission-overview",
    ),
    path(
        "mission/alerts",
        views.MissionAlertsView.as_view(),
        name="mission-alerts",
    ),
    path(
        "readings/<str:astronaut_id>",
        views.ReadingListView.as_view(),
        name="reading-list",
    ),
    path(
        "analysis/<str:astronaut_id>",
        views.StatisticalAnalysisView.as_view(),
        name="statistical-analysis",
    ),
    path(
        "baselines/<str:astronaut_id>",
        views.BaselineListView.as_view(),
        name="baseline-list",
    ),
    path(
        "baselines/<str:astronaut_id>/calculate",
        views.BaselineCalculateView.as_view(),
        name="baseline-calculate",
    ),
    path(
        "baselines/<str:astronaut_id>/history",
        views.BaselineHistoryView.as_view(),
        name="baseline-history",
    ),
]
