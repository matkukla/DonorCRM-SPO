"""
Tests for user detail endpoints in insights app.
"""
import pytest
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory
from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory
from apps.journals.models import Journal, JournalContact, Decision


@pytest.mark.django_db
class TestUserTrends:
    """Tests for GET /api/v1/insights/admin/user-trends/"""

    def test_admin_can_access(self, admin_client):
        """Admin can access user trends endpoint."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')
        response = client.get(f'/api/v1/insights/admin/user-trends/?user_id={staff.id}')
        assert response.status_code == status.HTTP_200_OK
        assert 'trends' in response.data
        assert 'weeks' in response.data

    def test_staff_cannot_access(self, authenticated_client):
        """Staff cannot access admin endpoint."""
        client, staff_user = authenticated_client
        response = client.get(f'/api/v1/insights/admin/user-trends/?user_id={staff_user.id}')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_user_id_returns_400(self, admin_client):
        """Request without user_id parameter returns 400."""
        client, admin_user = admin_client
        response = client.get('/api/v1/insights/admin/user-trends/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in response.data

    def test_returns_trend_data_structure(self, admin_client):
        """Verify trend data structure is correct."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')
        response = client.get(f'/api/v1/insights/admin/user-trends/?user_id={staff.id}')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['weeks'] == 12  # default
        assert isinstance(response.data['trends'], list)

        # Check structure of trend items
        if response.data['trends']:
            trend = response.data['trends'][0]
            assert 'week_start' in trend
            assert 'week_label' in trend
            assert 'decisions_logged' in trend
            assert 'donations_received' in trend
            assert 'stage_progressions' in trend

    def test_custom_weeks_parameter(self, admin_client):
        """Test custom weeks parameter."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')
        response = client.get(f'/api/v1/insights/admin/user-trends/?user_id={staff.id}&weeks=8')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['weeks'] == 8


@pytest.mark.django_db
class TestUserJournals:
    """Tests for GET /api/v1/insights/admin/user-journals/"""

    def test_admin_can_access(self, admin_client):
        """Admin can access user journals endpoint."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')
        response = client.get(f'/api/v1/insights/admin/user-journals/?user_id={staff.id}')
        assert response.status_code == status.HTTP_200_OK
        assert 'journals' in response.data

    def test_staff_cannot_access(self, authenticated_client):
        """Staff cannot access admin endpoint."""
        client, staff_user = authenticated_client
        response = client.get(f'/api/v1/insights/admin/user-journals/?user_id={staff_user.id}')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_user_id_returns_400(self, admin_client):
        """Request without user_id parameter returns 400."""
        client, admin_user = admin_client
        response = client.get('/api/v1/insights/admin/user-journals/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in response.data

    def test_returns_journals_for_user(self, admin_client):
        """Create a journal owned by a staff user, verify it appears in response."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')

        # Create a journal for the staff user
        journal = Journal.objects.create(
            name='Test Journal',
            owner=staff,
            goal_amount=Decimal('5000.00'),
        )

        # Add some contacts to the journal
        contact1 = ContactFactory(owner=staff)
        contact2 = ContactFactory(owner=staff)
        jc1 = JournalContact.objects.create(journal=journal, contact=contact1)
        jc2 = JournalContact.objects.create(journal=journal, contact=contact2)

        # Create a decision for one contact
        Decision.objects.create(
            journal_contact=jc1,
            amount=Decimal('100.00'),
            cadence='monthly'
        )

        response = client.get(f'/api/v1/insights/admin/user-journals/?user_id={staff.id}')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['journals']) == 1

        journal_data = response.data['journals'][0]
        assert journal_data['id'] == str(journal.id)
        assert journal_data['name'] == 'Test Journal'
        assert 'member_count' in journal_data
        assert 'decision_count' in journal_data
        assert 'active_member_count' in journal_data
        assert 'created_at' in journal_data

        # Verify counts
        assert journal_data['member_count'] == 2
        assert journal_data['decision_count'] == 1
        assert journal_data['active_member_count'] == 1
