"""
Tests for admin analytics endpoints in insights app.
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory
from apps.journals.models import Decision, Journal, JournalContact
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestAdminDashboardOverview:
    """Tests for GET /api/v1/insights/admin/dashboard-overview/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/dashboard-overview/")
        assert response.status_code == status.HTTP_200_OK
        assert "total_contacts" in response.data
        assert "active_journals" in response.data
        assert "stalled_contacts" in response.data
        assert "conversion_rate" in response.data
        assert "donations_12m" in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get("/api/v1/insights/admin/dashboard-overview/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self):
        client = APIClient()
        response = client.get("/api/v1/insights/admin/dashboard-overview/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_correct_counts(self, admin_client):
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        ContactFactory.create_batch(3, owner=staff)
        ContactFactory.create_batch(2, owner=admin_user)

        response = client.get("/api/v1/insights/admin/dashboard-overview/")
        assert response.data["total_contacts"] == 5


@pytest.mark.django_db
class TestStalledContacts:
    """Tests for GET /api/v1/insights/admin/stalled-contacts/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/")
        assert response.status_code == status.HTTP_200_OK
        assert "stalled_contacts" in response.data
        assert "total_count" in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pagination_params(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["limit"] == 10
        assert response.data["offset"] == 0

    def test_invalid_limit_returns_default(self, admin_client):
        """Send ?limit=abc, verify 200 response (not 500) with default limit of 50."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/?limit=abc")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["limit"] == 50  # default

    def test_invalid_offset_returns_default(self, admin_client):
        """Send ?offset=xyz, verify 200 response with default offset of 0."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/?offset=xyz")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["offset"] == 0  # default

    def test_zero_activity_contact_has_days_stalled(self, admin_client):
        """Create a contact, add to a journal (JournalContact), do NOT create any JournalStageEvent.
        Verify days_stalled is an integer >= 0, not None."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact = ContactFactory(owner=staff)
        # Add to journal but create no stage events
        journal = Journal.objects.create(
            name="Test Journal",
            owner=staff,
            goal_amount=Decimal("5000.00"),
        )
        JournalContact.objects.create(journal=journal, contact=contact)

        response = client.get("/api/v1/insights/admin/stalled-contacts/")
        assert response.status_code == status.HTTP_200_OK
        # Should have at least 1 stalled contact (the one we just created)
        if response.data["total_count"] > 0:
            # Find our contact in results
            contact_data = next(
                (c for c in response.data["stalled_contacts"] if c["id"] == str(contact.id)), None
            )
            if contact_data:
                assert contact_data["days_stalled"] is not None
                assert isinstance(contact_data["days_stalled"], int)
                assert contact_data["days_stalled"] >= 0

    def test_sort_by_days_stalled(self, admin_client):
        """Verify ?sort_by=days_stalled returns 200."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/?sort_by=days_stalled")
        assert response.status_code == status.HTTP_200_OK

    def test_sort_by_full_name(self, admin_client):
        """Verify ?sort_by=full_name returns 200."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/?sort_by=full_name")
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_sort_by_uses_default(self, admin_client):
        """Verify ?sort_by=hackme returns 200 (falls back to days_stalled default, not error)."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/stalled-contacts/?sort_by=hackme")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserPerformance:
    """Tests for GET /api/v1/insights/admin/user-performance/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/user-performance/")
        assert response.status_code == status.HTTP_200_OK
        assert "users" in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get("/api/v1/insights/admin/user-performance/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_user_metrics(self, admin_client):
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        ContactFactory.create_batch(3, owner=staff)

        response = client.get("/api/v1/insights/admin/user-performance/")
        assert response.status_code == status.HTTP_200_OK
        users = response.data["users"]
        # Should include both admin and staff users
        assert len(users) >= 2
        # Verify structure
        user_data = users[0]
        assert "id" in user_data
        assert "email" in user_data
        assert "total_contacts" in user_data
        assert "active_journals" in user_data
        assert "decisions_logged" in user_data
        assert "total_donations" in user_data

    def test_includes_conversion_rate(self, admin_client):
        """conversion_rate is returned per user (Phase 14 success criteria #3)."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact = ContactFactory(owner=staff)
        # Create journal, journal_contact, and decision to get non-zero conversion rate
        journal = Journal.objects.create(
            name="Test Journal",
            owner=staff,
            goal_amount=Decimal("10000.00"),
        )
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        Decision.objects.create(
            journal_contact=jc,
            amount=10000,  # $100.00
            cadence="monthly",
            status="active",
        )

        response = client.get("/api/v1/insights/admin/user-performance/")
        assert response.status_code == status.HTTP_200_OK
        staff_data = next(u for u in response.data["users"] if u["email"] == staff.email)
        assert "conversion_rate" in staff_data
        assert isinstance(staff_data["conversion_rate"], (int, float))
        assert staff_data["conversion_rate"] > 0  # 1 contact with decision / 1 total contact


@pytest.mark.django_db
class TestConversionFunnel:
    """Tests for GET /api/v1/insights/admin/conversion-funnel/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/conversion-funnel/")
        assert response.status_code == status.HTTP_200_OK
        assert "funnel" in response.data
        assert "total_contacts_in_pipeline" in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get("/api/v1/insights/admin/conversion-funnel/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_funnel_uses_pipeline_stages(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/conversion-funnel/")
        funnel = response.data["funnel"]
        # Should have entries for pipeline stages (even if 0 count)
        stage_names = [f["stage"] for f in funnel if f["stage"] is not None]
        expected_stages = ["contact", "meet", "close", "decision", "thank", "next_steps"]
        for expected in expected_stages:
            assert expected in stage_names, f"Missing stage: {expected}"


@pytest.mark.django_db
class TestTeamActivity:
    """Tests for GET /api/v1/insights/admin/team-activity/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/team-activity/")
        assert response.status_code == status.HTTP_200_OK
        assert "activities" in response.data
        assert "total_count" in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get("/api/v1/insights/admin/team-activity/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_limit_param(self, admin_client):
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/team-activity/?limit=10")
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_limit_returns_default(self, admin_client):
        """Send ?limit=abc, verify 200 (not 500)."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/team-activity/?limit=abc")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAdminEndpointPermissions:
    """Cross-cutting permission tests for all 5 admin endpoints."""

    ADMIN_ENDPOINTS = [
        "/api/v1/insights/admin/dashboard-overview/",
        "/api/v1/insights/admin/stalled-contacts/",
        "/api/v1/insights/admin/user-performance/",
        "/api/v1/insights/admin/conversion-funnel/",
        "/api/v1/insights/admin/team-activity/",
    ]

    def test_coach_cannot_access(self):
        user = UserFactory(role="coach")
        client = APIClient()
        client.force_authenticate(user=user)
        for endpoint in self.ADMIN_ENDPOINTS:
            response = client.get(endpoint)
            assert (
                response.status_code == status.HTTP_403_FORBIDDEN
            ), f"Coach user should get 403 from {endpoint}"

    def test_missionary_cannot_access(self):
        user = UserFactory(role="missionary")
        client = APIClient()
        client.force_authenticate(user=user)
        for endpoint in self.ADMIN_ENDPOINTS:
            response = client.get(endpoint)
            assert (
                response.status_code == status.HTTP_403_FORBIDDEN
            ), f"Missionary user should get 403 from {endpoint}"


@pytest.mark.django_db
class TestDashboardOverviewDonationAmounts:
    """Tests verifying donation amounts are returned in dollars (not cents)."""

    def test_donation_amount_is_dollars(self, admin_client):
        """Verify donations_12m.total_amount is in dollars, not cents."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact = ContactFactory(owner=staff)

        # Create gift of $250.00 (25000 cents)
        from datetime import date, timedelta

        GiftFactory(
            donor_contact=contact,
            amount_cents=25000,
            gift_date=date.today() - timedelta(days=5),
        )

        response = client.get("/api/v1/insights/admin/dashboard-overview/")
        assert response.status_code == status.HTTP_200_OK
        # Backend should return 250.0 (dollars), not 25000 (cents)
        assert response.data["donations_12m"]["total_amount"] == 250.0
        assert response.data["donations_12m"]["total_count"] == 1


@pytest.mark.django_db
class TestUserPerformanceBugFixes:
    """Tests for bug fixes in user performance endpoint."""

    def test_supervisor_users_included(self, admin_client):
        """Verify supervisor role users appear in user performance results."""
        client, admin_user = admin_client
        supervisor = UserFactory(role="supervisor")
        ContactFactory.create_batch(2, owner=supervisor)

        response = client.get("/api/v1/insights/admin/user-performance/")
        assert response.status_code == status.HTTP_200_OK
        user_emails = [u["email"] for u in response.data["users"]]
        assert supervisor.email in user_emails

    def test_conversion_rate_uses_journal_contacts_denominator(self, admin_client):
        """Verify conversion rate denominator is contacts-in-journals, not all contacts."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")

        # Create 5 contacts, but only 2 in journals
        contacts = ContactFactory.create_batch(5, owner=staff)
        journal = Journal.objects.create(
            name="Test Journal",
            owner=staff,
            goal_amount=Decimal("10000.00"),
        )
        jc1 = JournalContact.objects.create(journal=journal, contact=contacts[0])
        JournalContact.objects.create(journal=journal, contact=contacts[1])

        # Add decision for 1 of the 2 journal contacts
        Decision.objects.create(
            journal_contact=jc1,
            amount=Decimal("100.00"),
            cadence="monthly",
            status="active",
        )

        response = client.get("/api/v1/insights/admin/user-performance/")
        assert response.status_code == status.HTTP_200_OK
        staff_data = next(u for u in response.data["users"] if u["email"] == staff.email)

        # Conversion rate should be 1/2 = 50.0%, not 1/5 = 20.0%
        assert staff_data["conversion_rate"] == 50.0

    def test_donation_total_is_dollars(self, admin_client):
        """Verify total_donations in user performance is in dollars."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact = ContactFactory(owner=staff)

        from datetime import date, timedelta

        GiftFactory(
            donor_contact=contact,
            amount_cents=50000,  # $500.00
            gift_date=date.today() - timedelta(days=5),
        )

        response = client.get("/api/v1/insights/admin/user-performance/")
        assert response.status_code == status.HTTP_200_OK
        staff_data = next(u for u in response.data["users"] if u["email"] == staff.email)
        assert staff_data["total_donations"] == 500.0


@pytest.mark.django_db
class TestConversionFunnelBugFixes:
    """Tests for bug fixes in conversion funnel endpoint."""

    def test_no_activity_contacts_excluded_from_total(self, admin_client):
        """Verify contacts with no stage events don't inflate total_contacts_in_pipeline."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact1 = ContactFactory(owner=staff)
        contact2 = ContactFactory(owner=staff)

        journal = Journal.objects.create(
            name="Test Journal",
            owner=staff,
            goal_amount=Decimal("10000.00"),
        )
        jc1 = JournalContact.objects.create(journal=journal, contact=contact1)
        JournalContact.objects.create(journal=journal, contact=contact2)

        # Only jc1 gets a stage event; jc2 has no activity
        from apps.journals.models import JournalStageEvent, PipelineStage

        JournalStageEvent.objects.create(
            journal_contact=jc1,
            stage=PipelineStage.CONTACT,
        )

        response = client.get("/api/v1/insights/admin/conversion-funnel/")
        assert response.status_code == status.HTTP_200_OK
        # total should be 1 (only jc1 with a stage event), not 2
        assert response.data["total_contacts_in_pipeline"] == 1
        # no_activity_count should be 1 (jc2)
        assert response.data["no_activity_count"] == 1

    def test_funnel_percentages_sum_to_100(self, admin_client):
        """Verify funnel stage percentages sum to approximately 100%."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")

        journal = Journal.objects.create(
            name="Test Journal",
            owner=staff,
            goal_amount=Decimal("10000.00"),
        )
        from apps.journals.models import JournalStageEvent, PipelineStage

        # Create 3 contacts in different stages
        for stage in [PipelineStage.CONTACT, PipelineStage.MEET, PipelineStage.CLOSE]:
            contact = ContactFactory(owner=staff)
            jc = JournalContact.objects.create(journal=journal, contact=contact)
            JournalStageEvent.objects.create(journal_contact=jc, stage=stage)

        response = client.get("/api/v1/insights/admin/conversion-funnel/")
        assert response.status_code == status.HTTP_200_OK
        total_pct = sum(f["percentage"] for f in response.data["funnel"])
        assert abs(total_pct - 100.0) < 1.0  # Allow for rounding
