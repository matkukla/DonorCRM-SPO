"""
Tests for Dashboard API views.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestDashboardView:
    """Tests for main dashboard endpoint."""

    def test_get_dashboard(self):
        """Test getting full dashboard data."""
        user = UserFactory(role='staff')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/dashboard/')

        assert response.status_code == status.HTTP_200_OK
        assert 'what_changed' in response.data
        assert 'needs_attention' in response.data
        assert 'support_progress' in response.data

    def test_get_dashboard_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/v1/dashboard/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWhatChangedView:
    """Tests for what changed endpoint."""

    def test_get_what_changed(self):
        """Test getting what changed data."""
        user = UserFactory(role='staff')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/dashboard/what-changed/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_new' in response.data


@pytest.mark.django_db
class TestNeedsAttentionView:
    """Tests for needs attention endpoint."""

    def test_get_needs_attention(self):
        """Test getting needs attention data."""
        user = UserFactory(role='staff')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/dashboard/needs-attention/')

        assert response.status_code == status.HTTP_200_OK
        assert 'late_pledge_count' in response.data
        assert 'overdue_task_count' in response.data


@pytest.mark.django_db
class TestLateDonationsView:
    """Tests for late donations endpoint."""

    def test_get_late_donations(self):
        """Test getting late donations."""
        user = UserFactory(role='staff')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/dashboard/late-donations/')

        assert response.status_code == status.HTTP_200_OK
        assert 'late_donations' in response.data
        assert 'total_count' in response.data


@pytest.mark.django_db
class TestThankYouQueueView:
    """Tests for thank you queue endpoint."""

    def test_get_thank_you_queue(self):
        """Test getting thank you queue."""
        user = UserFactory(role='staff')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/dashboard/thank-you-queue/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSupportProgressView:
    """Tests for support progress endpoint."""

    def test_get_support_progress(self):
        """Test getting support progress."""
        user = UserFactory(role='staff')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/dashboard/support-progress/')

        assert response.status_code == status.HTTP_200_OK
        assert 'current_monthly_support' in response.data
        assert 'monthly_goal' in response.data
        assert 'percentage' in response.data
