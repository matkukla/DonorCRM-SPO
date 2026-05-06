"""
API URL configuration for DonorCRM.
All API endpoints are prefixed with /api/v1/
"""
from django.conf import settings
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.urls import include, path

from rest_framework.permissions import IsAuthenticated

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def health_check(request):
    """Health check endpoint for load balancers. Verifies the DB is reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})


# In production, require authentication for API docs; open in development
schema_permission = [IsAuthenticated] if not settings.DEBUG else []

urlpatterns = [
    # Health check
    path("health/", health_check, name="health-check"),
    # API Documentation (authenticated in production, open in development)
    path(
        "schema/", SpectacularAPIView.as_view(permission_classes=schema_permission), name="schema"
    ),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=schema_permission),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="schema", permission_classes=schema_permission),
        name="redoc",
    ),
    # Authentication
    path("auth/", include("apps.users.urls_auth")),
    # Core resources
    path("users/", include("apps.users.urls")),
    path("contacts/", include("apps.contacts.urls")),
    path("groups/", include("apps.groups.urls")),
    path("gifts/", include("apps.gifts.urls")),
    path(
        "donations/", include("apps.gifts.urls", namespace="gifts_donations_alias")
    ),  # backward-compatible alias
    path(
        "pledges/", include("apps.gifts.urls", namespace="gifts_pledges_alias")
    ),  # backward-compatible alias
    path("tasks/", include("apps.tasks.urls")),
    path("events/", include("apps.events.urls")),
    # Aggregations
    path("dashboard/", include("apps.dashboard.urls")),
    # Import/Export
    path("imports/", include("apps.imports.urls")),
    # Journals
    path("journals/", include("apps.journals.urls")),
    # Prayers
    path("prayers/", include("apps.prayers.urls")),
    # Goals
    path("goals/", include("apps.users.urls_goals")),
    # Insights/Reports
    path("insights/", include("apps.insights.urls")),
    # Feedback
    path("feedback/", include("apps.feedback.urls")),
]
