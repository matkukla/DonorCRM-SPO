"""
Tests for team trends endpoint.
"""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory
from apps.journals.models import Decision, Journal, JournalContact, JournalStageEvent, PipelineStage
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestTeamTrendsView:
    """Tests for GET /api/v1/insights/admin/team-trends/"""

    def test_admin_can_access(self, admin_client):
        """Admin user gets 200 response."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_200_OK
        assert "trends" in response.data
        assert "weeks" in response.data

    def test_staff_cannot_access(self, authenticated_client):
        """Non-admin user gets 403 response."""
        client, user = authenticated_client
        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self):
        """Unauthenticated request gets 401 response."""
        client = APIClient()
        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_12_data_points_by_default(self, admin_client):
        """Default response contains 12 weekly data points."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["weeks"] == 12
        assert len(response.data["trends"]) == 12

    def test_data_structure(self, admin_client):
        """Each trend data point has required fields."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_200_OK

        # Check first data point has all fields
        first_point = response.data["trends"][0]
        assert "week_start" in first_point
        assert "week_label" in first_point
        assert "decisions_logged" in first_point
        assert "donations_received" in first_point
        assert "stage_progressions" in first_point

        # Verify types
        assert isinstance(first_point["week_start"], str)
        assert isinstance(first_point["week_label"], str)
        assert isinstance(first_point["decisions_logged"], int)
        assert isinstance(first_point["donations_received"], int)
        assert isinstance(first_point["stage_progressions"], int)

    def test_custom_weeks_param(self, admin_client):
        """weeks parameter controls number of data points returned."""
        client, user = admin_client

        # Test 4 weeks
        response = client.get("/api/v1/insights/admin/team-trends/?weeks=4")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["weeks"] == 4
        assert len(response.data["trends"]) == 4

        # Test 26 weeks
        response = client.get("/api/v1/insights/admin/team-trends/?weeks=26")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["weeks"] == 26
        assert len(response.data["trends"]) == 26

    def test_empty_database_returns_zero_filled_weeks(self, admin_client):
        """Empty database returns 12 weeks with all counts at 0."""
        client, user = admin_client
        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["trends"]) == 12

        # All counts should be 0
        for point in response.data["trends"]:
            assert point["decisions_logged"] == 0
            assert point["donations_received"] == 0
            assert point["stage_progressions"] == 0

    def test_counts_decisions_by_week(self, admin_client):
        """Decisions are counted in the correct week."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact = ContactFactory(owner=staff)
        contact2 = ContactFactory(owner=staff)

        # Create journal and journal_contacts
        journal = Journal.objects.create(
            name="Test Journal",
            owner=staff,
            goal_amount=Decimal("5000.00"),
        )
        journal_contact1 = JournalContact.objects.create(
            journal=journal,
            contact=contact,
        )
        journal_contact2 = JournalContact.objects.create(
            journal=journal,
            contact=contact2,
        )

        # Create decisions in current week (one per journal_contact, as enforced by model)
        now = timezone.now()
        Decision.objects.create(
            journal_contact=journal_contact1,
            amount=Decimal("100.00"),
            cadence="monthly",
            status="active",
        )
        # Update created_at to current week
        Decision.objects.filter(journal_contact=journal_contact1).update(created_at=now)

        Decision.objects.create(
            journal_contact=journal_contact2,
            amount=Decimal("50.00"),
            cadence="one_time",
            status="pending",
        )
        # Update created_at to current week
        Decision.objects.filter(journal_contact=journal_contact2).update(
            created_at=now - timedelta(days=1)
        )

        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_200_OK

        # Last week (most recent) should have 2 decisions
        last_week = response.data["trends"][-1]
        assert last_week["decisions_logged"] == 2

    def test_counts_donations_by_week(self, admin_client):
        """Gifts are counted in the correct week."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact = ContactFactory(owner=staff)

        # Create gifts in current week (use same day to avoid week-boundary issues)
        today = timezone.now().date()
        GiftFactory(donor_contact=contact, gift_date=today, amount_cents=10000)
        GiftFactory(donor_contact=contact, gift_date=today, amount_cents=5000)

        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_200_OK

        # Last week should have 2 donations
        last_week = response.data["trends"][-1]
        assert last_week["donations_received"] == 2

    def test_counts_stage_progressions_by_week(self, admin_client):
        """JournalStageEvents are counted in the correct week."""
        client, admin_user = admin_client
        staff = UserFactory(role="missionary")
        contact = ContactFactory(owner=staff)

        # Create journal and journal_contact
        journal = Journal.objects.create(
            name="Test Journal",
            owner=staff,
            goal_amount=Decimal("5000.00"),
        )
        journal_contact = JournalContact.objects.create(
            journal=journal,
            contact=contact,
        )

        # Create stage events in current week
        now = timezone.now()
        JournalStageEvent.objects.create(
            journal_contact=journal_contact,
            stage=PipelineStage.CONTACT,
            created_at=now,
        )
        JournalStageEvent.objects.create(
            journal_contact=journal_contact,
            stage=PipelineStage.MEET,
            created_at=now - timedelta(days=1),
        )
        JournalStageEvent.objects.create(
            journal_contact=journal_contact,
            stage=PipelineStage.CLOSE,
            created_at=now - timedelta(days=3),
        )

        response = client.get("/api/v1/insights/admin/team-trends/")
        assert response.status_code == status.HTTP_200_OK

        # Last week should have 3 stage progressions
        last_week = response.data["trends"][-1]
        assert last_week["stage_progressions"] == 3

    def test_invalid_weeks_param_returns_default(self, admin_client):
        """Invalid weeks parameter returns default (12)."""
        client, user = admin_client

        # Test non-numeric
        response = client.get("/api/v1/insights/admin/team-trends/?weeks=abc")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["weeks"] == 12

    def test_weeks_param_respects_min_max_bounds(self, admin_client):
        """weeks parameter is bounded between 1 and 52."""
        client, user = admin_client

        # Test below min (should return 1)
        response = client.get("/api/v1/insights/admin/team-trends/?weeks=0")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["weeks"] == 1
        assert len(response.data["trends"]) == 1

        # Test above max (should return 52)
        response = client.get("/api/v1/insights/admin/team-trends/?weeks=100")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["weeks"] == 52
        assert len(response.data["trends"]) == 52
