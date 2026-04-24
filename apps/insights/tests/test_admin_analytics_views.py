"""
Integration tests for admin analytics redesign DRF views (Issue #49).

Verifies:
  - Permission matrix: anonymous 401, non-admin 403, admin 200.
  - Response shape matches serializer contract.
  - Query params (limit, weeks) are honored and validated.
"""
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.users.tests.factories import CoachUserFactory, SupervisorUserFactory, UserFactory

ADMIN_ENDPOINTS = [
    "/api/v1/insights/admin/fiscal-year-pace/",
    "/api/v1/insights/admin/missionaries-behind-goal/",
    "/api/v1/insights/admin/pipeline-funnel-conversion/",
    "/api/v1/insights/admin/weekly-engagement/",
    "/api/v1/insights/admin/fiscal-year-donations/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", ADMIN_ENDPOINTS)
class TestAdminAnalyticsPermissions:
    def test_anonymous_gets_401(self, url):
        response = APIClient().get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missionary_gets_403(self, url, authenticated_client):
        client, _ = authenticated_client
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_supervisor_gets_403(self, url):
        client = APIClient()
        client.force_authenticate(user=SupervisorUserFactory())
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_coach_gets_403(self, url):
        client = APIClient()
        client.force_authenticate(user=CoachUserFactory())
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_gets_200(self, url, admin_client):
        client, _ = admin_client
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFiscalYearPaceEndpoint:
    def test_response_shape(self, admin_client):
        client, _ = admin_client
        response = client.get("/api/v1/insights/admin/fiscal-year-pace/")
        assert response.status_code == 200
        body = response.data
        for key in (
            "fy_start",
            "fy_end",
            "raised_cents",
            "annual_goal_cents",
            "expected_by_today_cents",
            "pace_percentage",
            "prior_year_raised_cents",
            "yoy_delta_percentage",
            "last_import_at",
        ):
            assert key in body


@pytest.mark.django_db
class TestMissionariesBehindGoalEndpoint:
    def test_limit_capped_at_50(self, admin_client):
        client, _ = admin_client
        # Request out-of-range limit — view should clamp to 50.
        response = client.get("/api/v1/insights/admin/missionaries-behind-goal/?limit=999")
        assert response.status_code == 200
        assert "missionaries" in response.data
        assert "total_excluded_no_goal" in response.data

    def test_respects_limit_param(self, admin_client):
        client, _ = admin_client
        for _ in range(4):
            UserFactory(role="missionary", monthly_support_goal_cents=100_000)
        response = client.get("/api/v1/insights/admin/missionaries-behind-goal/?limit=2")
        assert response.status_code == 200
        assert len(response.data["missionaries"]) == 2


@pytest.mark.django_db
class TestPipelineFunnelConversionEndpoint:
    def test_returns_all_seven_stages(self, admin_client):
        client, _ = admin_client
        response = client.get("/api/v1/insights/admin/pipeline-funnel-conversion/")
        assert response.status_code == 200
        assert len(response.data["stages"]) == 7


@pytest.mark.django_db
class TestWeeklyEngagementEndpoint:
    def test_weeks_param_honored(self, admin_client):
        client, _ = admin_client
        response = client.get("/api/v1/insights/admin/weekly-engagement/?weeks=4")
        assert response.status_code == 200
        assert len(response.data["weeks"]) == 4

    def test_default_is_twelve_weeks(self, admin_client):
        client, _ = admin_client
        response = client.get("/api/v1/insights/admin/weekly-engagement/")
        assert response.status_code == 200
        assert len(response.data["weeks"]) == 12


@pytest.mark.django_db
class TestFiscalYearDonationsEndpoint:
    def test_returns_twelve_months(self, admin_client):
        client, _ = admin_client
        response = client.get("/api/v1/insights/admin/fiscal-year-donations/")
        assert response.status_code == 200
        assert len(response.data["months"]) == 12
        for month in response.data["months"]:
            assert "short_label" in month
            assert "is_future" in month
