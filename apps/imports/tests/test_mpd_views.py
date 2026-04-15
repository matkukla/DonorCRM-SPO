"""
Tests for MPD API views: MPDMyDataView and MPDOverviewView.

Covers monthly_average_snapshot field in both endpoints (MPD-01, MPD-02).
"""
import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.imports.models import MPDUpload, MPDSnapshot

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def missionary_user(db):
    return User.objects.create_user(
        email='missionary@example.com',
        password='testpass123',
        first_name='John',
        last_name='Doe',
        role='missionary',
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email='admin@example.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User',
        role='admin',
    )


@pytest.fixture
def mpd_upload(db, admin_user):
    return MPDUpload.objects.create(
        uploaded_by=admin_user,
        filename='mpd_report.csv',
        file_format='csv',
        status='completed',
    )


@pytest.mark.django_db
class TestMPDMyDataView:
    """Tests for MPDMyDataView GET /api/v1/imports/mpd/me/."""

    def test_mpd_my_data_includes_monthly_average(self, api_client, missionary_user, mpd_upload):
        """Snapshot monthly average is returned under monthly_average_snapshot key."""
        MPDSnapshot.objects.create(
            user=missionary_user,
            upload=mpd_upload,
            monthly_average=Decimal('1234.56'),
        )

        api_client.force_authenticate(user=missionary_user)
        url = reverse('imports:mpd-my-data')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['monthly_average_snapshot'] == '1234.56'

    def test_mpd_my_data_monthly_average_null(self, api_client, missionary_user, mpd_upload):
        """Snapshot monthly average is returned as null when not set."""
        MPDSnapshot.objects.create(
            user=missionary_user,
            upload=mpd_upload,
            monthly_average=None,
        )

        api_client.force_authenticate(user=missionary_user)
        url = reverse('imports:mpd-my-data')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['monthly_average_snapshot'] is None


@pytest.mark.django_db
class TestMPDOverviewView:
    """Tests for MPDOverviewView GET /api/v1/imports/mpd/overview/."""

    def test_mpd_overview_includes_monthly_average(self, api_client, missionary_user, admin_user, mpd_upload):
        """Snapshot monthly average is returned under monthly_average_snapshot key."""
        MPDSnapshot.objects.create(
            user=missionary_user,
            upload=mpd_upload,
            monthly_average=Decimal('5678.00'),
        )

        api_client.force_authenticate(user=admin_user)
        url = reverse('imports:mpd-overview')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        missionaries = response.data['missionaries']
        assert len(missionaries) == 1
        assert missionaries[0]['monthly_average_snapshot'] == '5678.00'

    def test_mpd_overview_admin_only(self, api_client, missionary_user):
        """Non-admin users receive 403 Forbidden."""
        api_client.force_authenticate(user=missionary_user)
        url = reverse('imports:mpd-overview')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
