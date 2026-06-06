"""
Behavioral coverage tests for apps/insights/views.py.

Focuses on previously-untested view branches:
  - Financial-role gating (coach -> 403) on the four donor-finance endpoints
  - Happy-path payloads for donations-by-month/year, monthly-commitments,
    late-donations, follow-ups
  - Admin transactions ledger (filters, pagination, non-admin 403)
  - Single-user-performance 200 vs 404
  - Date-range / param-validation branches on admin analytics views

Time is pinned mid-fiscal-year where gift dates matter.
"""

from datetime import date

from rest_framework import status
from rest_framework.test import APIClient

import pytest
from freezegun import freeze_time

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.tasks.models import TaskStatus
from apps.tasks.tests.factories import TaskFactory
from apps.users.tests.factories import UserFactory


def _client_for(role):
    user = UserFactory(role=role)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


# Endpoints gated by is_financial_role (coach must be rejected).
FINANCIAL_ENDPOINTS = [
    "/api/v1/insights/donations-by-month/",
    "/api/v1/insights/donations-by-year/",
    "/api/v1/insights/monthly-commitments/",
    "/api/v1/insights/late-donations/",
]


@pytest.mark.django_db
class TestFinancialRoleGating:
    @pytest.mark.parametrize("endpoint", FINANCIAL_ENDPOINTS)
    def test_coach_forbidden(self, endpoint):
        client, _ = _client_for("coach")
        response = client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Not authorized"

    @pytest.mark.parametrize("endpoint", FINANCIAL_ENDPOINTS)
    def test_missionary_allowed(self, endpoint):
        client, _ = _client_for("missionary")
        response = client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("endpoint", FINANCIAL_ENDPOINTS)
    def test_unauthenticated_rejected(self, endpoint):
        response = APIClient().get(endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDonationsByMonthView:
    def test_returns_year_payload(self):
        client, user = _client_for("missionary")
        contact = ContactFactory(owner=user)
        GiftFactory(donor_contact=contact, amount_cents=30000, gift_date=date(2026, 3, 1))
        response = client.get("/api/v1/insights/donations-by-month/?year=2026")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["year"] == 2026
        assert len(response.data["months"]) == 12
        assert response.data["year_total"] == 300.0

    def test_invalid_year_param_falls_back(self):
        client, _ = _client_for("missionary")
        response = client.get("/api/v1/insights/donations-by-month/?year=abc")
        # get_safe_year_param sanitizes bad input -> still 200.
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["months"]) == 12


@pytest.mark.django_db
class TestDonationsByYearView:
    @freeze_time("2026-10-15")
    def test_returns_n_years(self):
        client, user = _client_for("missionary")
        contact = ContactFactory(owner=user)
        GiftFactory(donor_contact=contact, amount_cents=50000, gift_date=date(2026, 2, 1))
        response = client.get("/api/v1/insights/donations-by-year/?years=3")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["years"]) == 3
        assert response.data["grand_total"] == 500.0

    def test_years_param_clamped(self):
        client, _ = _client_for("missionary")
        # max_val=50; an out-of-range value is clamped, response still 200.
        response = client.get("/api/v1/insights/donations-by-year/?years=9999")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["years"]) == 50


@pytest.mark.django_db
class TestMonthlyCommitmentsView:
    def test_returns_active_pledges(self):
        client, user = _client_for("missionary")
        contact = ContactFactory(owner=user)
        RecurringGiftFactory(donor_contact=contact, amount_cents=10000)
        response = client.get("/api/v1/insights/monthly-commitments/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["active_count"] == 1
        assert response.data["total_monthly"] == pytest.approx(100.0, rel=0.01)


@pytest.mark.django_db
class TestLateDonationsView:
    def test_returns_late_payload(self):
        client, _ = _client_for("missionary")
        response = client.get("/api/v1/insights/late-donations/?limit=25")
        assert response.status_code == status.HTTP_200_OK
        assert "late_donations" in response.data
        assert "total_count" in response.data


@pytest.mark.django_db
class TestFollowUpsView:
    @freeze_time("2026-10-15")
    def test_returns_incomplete_tasks(self):
        client, user = _client_for("missionary")
        contact = ContactFactory(owner=user)
        TaskFactory(
            owner=user,
            contact=contact,
            status=TaskStatus.PENDING,
            due_date=date(2026, 10, 10),
        )
        response = client.get("/api/v1/insights/follow-ups/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 1
        assert response.data["overdue_count"] == 1

    def test_coach_allowed_follow_ups(self):
        # follow-ups is NOT financial-gated; a coach should get a 200.
        client, _ = _client_for("coach")
        response = client.get("/api/v1/insights/follow-ups/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTransactionsView:
    def test_admin_can_access_with_filters(self):
        client, _ = _client_for("admin")
        contact = ContactFactory()
        GiftFactory(donor_contact=contact, amount_cents=12300, gift_date=date(2026, 6, 1))
        response = client.get(
            "/api/v1/insights/transactions/?limit=10&offset=0"
            f"&contact_id={contact.id}&date_from=2026-01-01&date_to=2026-12-31"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 1
        assert response.data["transactions"][0]["amount"] == 123.0
        assert response.data["limit"] == 10
        assert response.data["offset"] == 0

    def test_missionary_forbidden(self):
        client, _ = _client_for("missionary")
        response = client.get("/api/v1/insights/transactions/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_date_returns_400(self):
        client, _ = _client_for("admin")
        response = client.get("/api/v1/insights/transactions/?date_from=not-a-date")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSingleUserPerformanceView:
    def test_returns_200_for_existing_user(self):
        client, _ = _client_for("admin")
        missionary = UserFactory(role="missionary")
        ContactFactory(owner=missionary)
        response = client.get(f"/api/v1/insights/admin/user-performance/{missionary.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(missionary.id)
        assert response.data["total_contacts"] == 1

    def test_returns_404_for_missing_user(self):
        import uuid

        client, _ = _client_for("admin")
        response = client.get(f"/api/v1/insights/admin/user-performance/{uuid.uuid4()}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_admin_forbidden(self):
        client, _ = _client_for("missionary")
        target = UserFactory(role="missionary")
        response = client.get(f"/api/v1/insights/admin/user-performance/{target.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminAnalyticsDateBranches:
    """Hit the date_from/date_to + param-validation branches on admin views."""

    def test_dashboard_overview_with_date_range(self):
        client, _ = _client_for("admin")
        response = client.get(
            "/api/v1/insights/admin/dashboard-overview/" "?date_from=2026-01-01&date_to=2026-12-31"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "donations_12m" in response.data

    def test_conversion_funnel_with_date_range(self):
        client, _ = _client_for("admin")
        response = client.get(
            "/api/v1/insights/admin/conversion-funnel/" "?date_from=2026-01-01&date_to=2026-12-31"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "funnel" in response.data

    def test_conversion_funnel_invalid_date_returns_400(self):
        client, _ = _client_for("admin")
        response = client.get("/api/v1/insights/admin/conversion-funnel/?date_to=garbage")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_team_activity_with_date_range(self):
        client, _ = _client_for("admin")
        response = client.get(
            "/api/v1/insights/admin/team-activity/"
            "?limit=5&date_from=2026-01-01&date_to=2026-12-31"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "activities" in response.data

    def test_team_activity_invalid_date_returns_400(self):
        client, _ = _client_for("admin")
        response = client.get("/api/v1/insights/admin/team-activity/?date_from=bad")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_stalled_contacts_invalid_date_returns_400(self):
        client, _ = _client_for("admin")
        response = client.get("/api/v1/insights/admin/stalled-contacts/?date_from=bad")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_stalled_contacts_invalid_sort_dir_falls_back(self):
        # An out-of-allowlist sort_dir is coerced to "desc" (still 200).
        client, _ = _client_for("admin")
        response = client.get("/api/v1/insights/admin/stalled-contacts/?sort_dir=sideways")
        assert response.status_code == status.HTTP_200_OK

    def test_team_trends_invalid_date_returns_400(self):
        client, _ = _client_for("admin")
        response = client.get("/api/v1/insights/admin/team-trends/?date_from=nope")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
