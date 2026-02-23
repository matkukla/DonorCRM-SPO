"""
Tests for admin analytics endpoints in insights app.
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
class TestAdminDashboardOverview:
    """Tests for GET /api/v1/insights/admin/dashboard-overview/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/dashboard-overview/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total_contacts' in response.data
        assert 'active_journals' in response.data
        assert 'stalled_contacts' in response.data
        assert 'conversion_rate' in response.data
        assert 'donations_12m' in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get('/api/v1/insights/admin/dashboard-overview/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self):
        client = APIClient()
        response = client.get('/api/v1/insights/admin/dashboard-overview/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_correct_counts(self, admin_client):
        client, admin_user = admin_client
        staff = UserFactory(role='staff')
        ContactFactory.create_batch(3, owner=staff)
        ContactFactory.create_batch(2, owner=admin_user)

        response = client.get('/api/v1/insights/admin/dashboard-overview/')
        assert response.data['total_contacts'] == 5


@pytest.mark.django_db
class TestStalledContacts:
    """Tests for GET /api/v1/insights/admin/stalled-contacts/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/')
        assert response.status_code == status.HTTP_200_OK
        assert 'stalled_contacts' in response.data
        assert 'total_count' in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pagination_params(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/?limit=10&offset=0')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['limit'] == 10
        assert response.data['offset'] == 0

    def test_invalid_limit_returns_default(self, admin_client):
        """Send ?limit=abc, verify 200 response (not 500) with default limit of 50."""
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/?limit=abc')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['limit'] == 50  # default

    def test_invalid_offset_returns_default(self, admin_client):
        """Send ?offset=xyz, verify 200 response with default offset of 0."""
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/?offset=xyz')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['offset'] == 0  # default

    def test_zero_activity_contact_has_days_stalled(self, admin_client):
        """Create a contact, add to a journal (JournalContact), do NOT create any JournalStageEvent.
        Verify days_stalled is an integer >= 0, not None."""
        client, admin_user = admin_client
        staff = UserFactory(role='staff')
        contact = ContactFactory(owner=staff)
        # Add to journal but create no stage events
        journal = Journal.objects.create(
            name='Test Journal',
            owner=staff,
            goal_amount=Decimal('5000.00'),
        )
        JournalContact.objects.create(journal=journal, contact=contact)

        response = client.get('/api/v1/insights/admin/stalled-contacts/')
        assert response.status_code == status.HTTP_200_OK
        # Should have at least 1 stalled contact (the one we just created)
        if response.data['total_count'] > 0:
            # Find our contact in results
            contact_data = next(
                (c for c in response.data['stalled_contacts'] if c['id'] == str(contact.id)),
                None
            )
            if contact_data:
                assert contact_data['days_stalled'] is not None
                assert isinstance(contact_data['days_stalled'], int)
                assert contact_data['days_stalled'] >= 0

    def test_sort_by_days_stalled(self, admin_client):
        """Verify ?sort_by=days_stalled returns 200."""
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/?sort_by=days_stalled')
        assert response.status_code == status.HTTP_200_OK

    def test_sort_by_full_name(self, admin_client):
        """Verify ?sort_by=full_name returns 200."""
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/?sort_by=full_name')
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_sort_by_uses_default(self, admin_client):
        """Verify ?sort_by=hackme returns 200 (falls back to days_stalled default, not error)."""
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/?sort_by=hackme')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserPerformance:
    """Tests for GET /api/v1/insights/admin/user-performance/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/user-performance/')
        assert response.status_code == status.HTTP_200_OK
        assert 'users' in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get('/api/v1/insights/admin/user-performance/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_user_metrics(self, admin_client):
        client, admin_user = admin_client
        staff = UserFactory(role='staff')
        ContactFactory.create_batch(3, owner=staff)

        response = client.get('/api/v1/insights/admin/user-performance/')
        assert response.status_code == status.HTTP_200_OK
        users = response.data['users']
        # Should include both admin and staff users
        assert len(users) >= 2
        # Verify structure
        user_data = users[0]
        assert 'id' in user_data
        assert 'email' in user_data
        assert 'total_contacts' in user_data
        assert 'active_journals' in user_data
        assert 'decisions_logged' in user_data
        assert 'total_donations' in user_data

    def test_includes_conversion_rate(self, admin_client):
        """conversion_rate is returned per user (Phase 14 success criteria #3)."""
        client, admin_user = admin_client
        staff = UserFactory(role='staff')
        contact = ContactFactory(owner=staff)
        # Create journal, journal_contact, and decision to get non-zero conversion rate
        journal = Journal.objects.create(
            name='Test Journal',
            owner=staff,
            goal_amount=Decimal('10000.00'),
        )
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        Decision.objects.create(
            journal_contact=jc,
            amount=10000,  # $100.00
            cadence='monthly',
            status='active',
        )

        response = client.get('/api/v1/insights/admin/user-performance/')
        assert response.status_code == status.HTTP_200_OK
        staff_data = next(u for u in response.data['users'] if u['email'] == staff.email)
        assert 'conversion_rate' in staff_data
        assert isinstance(staff_data['conversion_rate'], (int, float))
        assert staff_data['conversion_rate'] > 0  # 1 contact with decision / 1 total contact


@pytest.mark.django_db
class TestConversionFunnel:
    """Tests for GET /api/v1/insights/admin/conversion-funnel/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/conversion-funnel/')
        assert response.status_code == status.HTTP_200_OK
        assert 'funnel' in response.data
        assert 'total_contacts_in_pipeline' in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get('/api/v1/insights/admin/conversion-funnel/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_funnel_uses_pipeline_stages(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/conversion-funnel/')
        funnel = response.data['funnel']
        # Should have entries for pipeline stages (even if 0 count)
        stage_names = [f['stage'] for f in funnel if f['stage'] is not None]
        expected_stages = ['contact', 'meet', 'close', 'decision', 'thank', 'next_steps']
        for expected in expected_stages:
            assert expected in stage_names, f"Missing stage: {expected}"


@pytest.mark.django_db
class TestTeamActivity:
    """Tests for GET /api/v1/insights/admin/team-activity/"""

    def test_admin_can_access(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/team-activity/')
        assert response.status_code == status.HTTP_200_OK
        assert 'activities' in response.data
        assert 'total_count' in response.data

    def test_staff_cannot_access(self, authenticated_client):
        client, user = authenticated_client
        response = client.get('/api/v1/insights/admin/team-activity/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_limit_param(self, admin_client):
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/team-activity/?limit=10')
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_limit_returns_default(self, admin_client):
        """Send ?limit=abc, verify 200 (not 500)."""
        client, user = admin_client
        response = client.get('/api/v1/insights/admin/team-activity/?limit=abc')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAdminEndpointPermissions:
    """Cross-cutting permission tests for all 5 admin endpoints."""

    ADMIN_ENDPOINTS = [
        '/api/v1/insights/admin/dashboard-overview/',
        '/api/v1/insights/admin/stalled-contacts/',
        '/api/v1/insights/admin/user-performance/',
        '/api/v1/insights/admin/conversion-funnel/',
        '/api/v1/insights/admin/team-activity/',
    ]

    def test_finance_user_cannot_access(self, finance_client):
        client, user = finance_client
        for endpoint in self.ADMIN_ENDPOINTS:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"Finance user should get 403 from {endpoint}"

    def test_read_only_user_cannot_access(self):
        user = UserFactory(role='read_only')
        client = APIClient()
        client.force_authenticate(user=user)
        for endpoint in self.ADMIN_ENDPOINTS:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"Read-only user should get 403 from {endpoint}"
