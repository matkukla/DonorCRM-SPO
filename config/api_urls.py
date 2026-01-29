"""
API URL configuration for DonorCRM.
All API endpoints are prefixed with /api/v1/
"""
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def health_check(request):
    """Simple health check endpoint for load balancers."""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    # Health check
    path('health/', health_check, name='health-check'),

    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Authentication
    path('auth/', include('apps.users.urls_auth')),

    # Core resources
    path('users/', include('apps.users.urls')),
    path('contacts/', include('apps.contacts.urls')),
    path('groups/', include('apps.groups.urls')),
    path('donations/', include('apps.donations.urls')),
    path('pledges/', include('apps.pledges.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('events/', include('apps.events.urls')),

    # Aggregations
    path('dashboard/', include('apps.dashboard.urls')),

    # Import/Export
    path('imports/', include('apps.imports.urls')),

    # Journals
    path('journals/', include('apps.journals.urls')),

    # Insights/Reports
    path('insights/', include('apps.insights.urls')),
]
