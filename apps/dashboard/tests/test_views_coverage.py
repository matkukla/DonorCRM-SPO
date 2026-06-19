"""
Behavioral coverage tests for dashboard views.

Focuses on the _resolve_target_user permission branches (admin/supervisor
selecting another user, missionary denial, invalid/missing user_id), the
mark-seen endpoint, the per-user layout endpoint, and JSON payload values
for the giving/monthly/recent-gift tiles (dollars derived from cents).
"""

import uuid
from datetime import date

from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.models import Gift, RecurringGift, RecurringGiftFrequency, RecurringGiftStatus
from apps.users.tests.factories import AdminUserFactory, SupervisorUserFactory, UserFactory


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestResolveTargetUserViaDashboard:
    """_resolve_target_user is exercised through DashboardView (?user_id=)."""

    def test_admin_can_select_another_user(self):
        admin = AdminUserFactory(email="resolve-admin@test.com")
        target = UserFactory(role="missionary", email="resolve-target@test.com")
        response = _client(admin).get(f"/api/v1/dashboard/?user_id={target.id}")
        assert response.status_code == status.HTTP_200_OK
        assert "support_progress" in response.data

    def test_supervisor_can_select_assigned_user(self):
        supervisor = SupervisorUserFactory()
        target = UserFactory(role="missionary", email="resolve-sup-target@test.com")
        target.supervisors.add(supervisor)
        response = _client(supervisor).get(f"/api/v1/dashboard/?user_id={target.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_supervisor_cannot_select_unassigned_user(self):
        supervisor = SupervisorUserFactory()
        target = UserFactory(role="missionary", email="resolve-sup-unassigned@test.com")
        response = _client(supervisor).get(f"/api/v1/dashboard/?user_id={target.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missionary_cannot_select_another_user(self):
        missionary = UserFactory(role="missionary", email="resolve-miss@test.com")
        other = UserFactory(role="missionary", email="resolve-other@test.com")
        response = _client(missionary).get(f"/api/v1/dashboard/?user_id={other.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_id_equal_to_self_is_allowed(self):
        missionary = UserFactory(role="missionary", email="resolve-self@test.com")
        response = _client(missionary).get(f"/api/v1/dashboard/?user_id={missionary.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_user_id_returns_404(self):
        admin = AdminUserFactory(email="resolve-bad@test.com")
        response = _client(admin).get("/api/v1/dashboard/?user_id=not-a-uuid")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_user_id_returns_404(self):
        admin = AdminUserFactory(email="resolve-missing@test.com")
        response = _client(admin).get(f"/api/v1/dashboard/?user_id={uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_inactive_user_id_returns_404(self):
        admin = AdminUserFactory(email="resolve-inactive@test.com")
        inactive = UserFactory(role="missionary", email="resolve-dead@test.com", is_active=False)
        response = _client(admin).get(f"/api/v1/dashboard/?user_id={inactive.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestMarkEventsSeenView:
    def test_mark_seen_returns_detail(self):
        user = UserFactory(role="missionary", email="mark-seen@test.com")
        response = _client(user).post("/api/v1/dashboard/mark-seen/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Events marked as seen."

    def test_mark_seen_requires_auth(self):
        response = APIClient().post("/api/v1/dashboard/mark-seen/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGivingSummaryView:
    def test_giving_summary_reflects_gift_totals(self):
        user = UserFactory(
            role="missionary",
            email="giving@test.com",
            monthly_support_goal_cents=200000,
        )
        contact = ContactFactory(owner=user)
        # Gift dated within the current fiscal year.
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=40000,
            gift_date=date.today(),
        )
        response = _client(user).get("/api/v1/dashboard/giving-summary/")
        assert response.status_code == status.HTTP_200_OK
        # 40000 cents == $400 given this fiscal year.
        assert response.data["given"] == 400.0
        assert response.data["monthly_goal"] == 2000.0
        assert response.data["annual_goal"] == 24000.0
        assert "expecting" in response.data
        assert "fiscal_year_label" in response.data


@pytest.mark.django_db
class TestMonthlyGiftsView:
    def test_monthly_gifts_returns_requested_window(self):
        user = UserFactory(role="missionary", email="monthly@test.com")
        contact = ContactFactory(owner=user)
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=15000,
            gift_date=date.today().replace(day=1),
        )
        response = _client(user).get("/api/v1/dashboard/monthly-gifts/?months=3")
        assert response.status_code == status.HTTP_200_OK
        months = response.data["months"]
        assert len(months) == 3
        # Current month bucket should include the $150 gift.
        current_key = date.today().strftime("%Y-%m")
        current = next(m for m in months if m["month"] == current_key)
        assert current["total"] == 150.0

    def test_monthly_gifts_clamps_invalid_months_param(self):
        user = UserFactory(role="missionary", email="monthly-bad@test.com")
        response = _client(user).get("/api/v1/dashboard/monthly-gifts/?months=abc")
        # Invalid param falls back to the default of 12.
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["months"]) == 12


@pytest.mark.django_db
class TestRecentGiftsView:
    def test_recent_gifts_includes_recent_gift(self):
        user = UserFactory(role="missionary", email="recent@test.com")
        contact = ContactFactory(owner=user, first_name="Rita", last_name="Recent")
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=7500,
            gift_date=date.today(),
        )
        response = _client(user).get("/api/v1/dashboard/recent-gifts/?days=30&limit=5")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["days"] == 30
        gifts = response.data["recent_gifts"]
        assert len(gifts) == 1
        assert str(gifts[0]["amount_cents"]) == "7500" or gifts[0]["amount_cents"] == 7500

    def test_recent_gifts_excludes_old_gifts(self):
        user = UserFactory(role="missionary", email="recent-old@test.com")
        contact = ContactFactory(owner=user)
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=9000,
            gift_date=date.today() - timezone.timedelta(days=400),
        )
        response = _client(user).get("/api/v1/dashboard/recent-gifts/?days=30")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["recent_gifts"] == []


@pytest.mark.django_db
class TestLateDonationsAndThankYouViews:
    def test_late_donations_payload_shape(self):
        user = UserFactory(role="missionary", email="late@test.com")
        response = _client(user).get("/api/v1/dashboard/late-donations/?limit=5")
        assert response.status_code == status.HTTP_200_OK
        assert "late_donations" in response.data
        assert response.data["total_count"] == len(response.data["late_donations"])

    def test_thank_you_queue_counts_flagged_contacts(self):
        user = UserFactory(role="missionary", email="thanks@test.com")
        ContactFactory(
            owner=user,
            first_name="Thank",
            last_name="Me",
            needs_thank_you=True,
        )
        ContactFactory(
            owner=user,
            first_name="No",
            last_name="Thanks",
            needs_thank_you=False,
        )
        response = _client(user).get("/api/v1/dashboard/thank-you-queue/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_count"] == 1
        names = [c.get("full_name", "") for c in response.data["thank_you_queue"]]
        assert any("Thank" in (n or "") for n in names)

    def test_support_progress_percentage(self):
        user = UserFactory(
            role="missionary",
            email="support@test.com",
            monthly_support_goal_cents=100000,
        )
        contact = ContactFactory(owner=user)
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=50000,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=date.today(),
        )
        response = _client(user).get("/api/v1/dashboard/support-progress/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["monthly_goal"] == 1000.0
        # $500/mo recurring against a $1000 goal => 50%.
        assert response.data["recurring_monthly"] == 500.0
        assert response.data["percentage"] == 50.0


@pytest.mark.django_db
class TestUserDashboardLayoutView:
    def _url(self, pk):
        return f"/api/v1/dashboard/user/{pk}/layout/"

    def test_admin_can_view_user_layout(self):
        admin = AdminUserFactory(email="layout-admin@test.com")
        target = UserFactory(
            role="missionary",
            email="layout-target@test.com",
            dashboard_layout={"widgets": ["giving", "tasks"]},
        )
        response = _client(admin).get(self._url(target.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["dashboard_layout"] == {"widgets": ["giving", "tasks"]}

    def test_layout_defaults_to_empty_dict(self):
        admin = AdminUserFactory(email="layout-empty@test.com")
        # dashboard_layout is NOT NULL (defaults to {}); empty dict exercises
        # the view's `target.dashboard_layout or {}` fallback branch.
        target = UserFactory(
            role="missionary",
            email="layout-empty-target@test.com",
            dashboard_layout={},
        )
        response = _client(admin).get(self._url(target.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["dashboard_layout"] == {}

    def test_missionary_cannot_view_other_user_layout(self):
        missionary = UserFactory(role="missionary", email="layout-miss@test.com")
        other = UserFactory(role="missionary", email="layout-other@test.com")
        response = _client(missionary).get(self._url(other.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_layout_nonexistent_user_returns_404(self):
        admin = AdminUserFactory(email="layout-404@test.com")
        response = _client(admin).get(self._url(uuid.uuid4()))
        assert response.status_code == status.HTTP_404_NOT_FOUND
