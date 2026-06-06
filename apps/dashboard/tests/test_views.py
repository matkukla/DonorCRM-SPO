"""
Tests for Dashboard API views.
"""

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.users.tests.factories import AdminUserFactory, SupervisorUserFactory, UserFactory


@pytest.mark.django_db
class TestDashboardView:
    """Tests for main dashboard endpoint."""

    def test_get_dashboard(self):
        """Test getting full dashboard data."""
        user = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/dashboard/")

        assert response.status_code == status.HTTP_200_OK
        assert "what_changed" in response.data
        assert "needs_attention" in response.data
        assert "support_progress" in response.data

    def test_get_dashboard_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get("/api/v1/dashboard/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWhatChangedView:
    """Tests for what changed endpoint."""

    def test_get_what_changed(self):
        """Test getting what changed data."""
        user = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/dashboard/what-changed/")

        assert response.status_code == status.HTTP_200_OK
        assert "total_new" in response.data


@pytest.mark.django_db
class TestNeedsAttentionView:
    """Tests for needs attention endpoint."""

    def test_get_needs_attention(self):
        """Test getting needs attention data."""
        user = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/dashboard/needs-attention/")

        assert response.status_code == status.HTTP_200_OK
        assert "late_pledge_count" in response.data
        assert "overdue_task_count" in response.data


@pytest.mark.django_db
class TestLateDonationsView:
    """Tests for late donations endpoint."""

    def test_get_late_donations(self):
        """Test getting late donations."""
        user = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/dashboard/late-donations/")

        assert response.status_code == status.HTTP_200_OK
        assert "late_donations" in response.data
        assert "total_count" in response.data


@pytest.mark.django_db
class TestThankYouQueueView:
    """Tests for thank you queue endpoint."""

    def test_get_thank_you_queue(self):
        """Test getting thank you queue."""
        user = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/dashboard/thank-you-queue/")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSupportProgressView:
    """Tests for support progress endpoint."""

    def test_get_support_progress(self):
        """Test getting support progress."""
        user = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/dashboard/support-progress/")

        assert response.status_code == status.HTTP_200_OK
        assert "current_monthly_support" in response.data
        assert "monthly_goal" in response.data
        assert "percentage" in response.data


@pytest.mark.django_db
class TestResolveTargetUser:
    """Tests for _resolve_target_user() dashboard selection permissions."""

    def test_supervisor_can_view_missionary_dashboard(self):
        """Supervisor may select any missionary via ?user_id= (dashboard dropdown)."""
        supervisor = SupervisorUserFactory()
        missionary = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=supervisor)

        response = client.get(f"/api/v1/dashboard/?user_id={missionary.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_view_missionary_dashboard(self):
        """Admin may select any missionary via ?user_id= (dashboard dropdown)."""
        admin = AdminUserFactory()
        missionary = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(f"/api/v1/dashboard/?user_id={missionary.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_missionary_cannot_view_other_missionary_dashboard(self):
        """Missionary may not pass a different user's ID — receives 403."""
        missionary1 = UserFactory(role="missionary")
        missionary2 = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=missionary1)

        response = client.get(f"/api/v1/dashboard/?user_id={missionary2.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_supervisor_with_nonexistent_user_id_returns_404(self):
        """Supervisor passing a non-existent user_id receives 404 (not 403)."""
        import uuid

        supervisor = SupervisorUserFactory()

        client = APIClient()
        client.force_authenticate(user=supervisor)

        nonexistent_id = uuid.uuid4()
        response = client.get(f"/api/v1/dashboard/?user_id={nonexistent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
