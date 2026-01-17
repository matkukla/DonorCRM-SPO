"""
Tests for Pledge API views.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.tests.factories import ContactFactory
from apps.pledges.models import Pledge, PledgeStatus
from apps.pledges.tests.factories import PledgeFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestPledgeListCreateView:
    """Tests for pledge list and create endpoints."""

    def test_list_pledges_authenticated(self):
        """Test listing pledges for authenticated user."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        PledgeFactory.create_batch(3, contact=contact)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/pledges/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_list_pledges_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/v1/pledges/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_pledge(self):
        """Test creating a pledge."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            'contact': str(contact.id),
            'amount': '150.00',
            'frequency': 'monthly',
            'start_date': str(timezone.now().date())
        }

        response = client.post('/api/v1/pledges/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount'] == '150.00'
        assert response.data['status'] == 'active'

    def test_staff_only_sees_own_contacts_pledges(self):
        """Test that staff only sees pledges from their contacts."""
        user1 = UserFactory(role='staff')
        user2 = UserFactory(role='staff')
        contact1 = ContactFactory(owner=user1)
        contact2 = ContactFactory(owner=user2)
        PledgeFactory.create_batch(2, contact=contact1)
        PledgeFactory.create_batch(3, contact=contact2)

        client = APIClient()
        client.force_authenticate(user=user1)

        response = client.get('/api/v1/pledges/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2


@pytest.mark.django_db
class TestPledgeDetailView:
    """Tests for pledge detail endpoint."""

    def test_get_pledge_detail(self):
        """Test getting pledge detail."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        pledge = PledgeFactory(contact=contact, amount=Decimal('200.00'))

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f'/api/v1/pledges/{pledge.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['amount'] == '200.00'

    def test_update_pledge(self):
        """Test updating a pledge."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        pledge = PledgeFactory(contact=contact)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch(
            f'/api/v1/pledges/{pledge.id}/',
            {'notes': 'Updated notes'}
        )

        assert response.status_code == status.HTTP_200_OK
        pledge.refresh_from_db()
        assert pledge.notes == 'Updated notes'


@pytest.mark.django_db
class TestPledgeActionViews:
    """Tests for pledge action endpoints (pause, resume, cancel)."""

    def test_pause_pledge(self):
        """Test pausing a pledge."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        pledge = PledgeFactory(contact=contact, status=PledgeStatus.ACTIVE)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'/api/v1/pledges/{pledge.id}/pause/')

        assert response.status_code == status.HTTP_200_OK
        pledge.refresh_from_db()
        assert pledge.status == PledgeStatus.PAUSED

    def test_resume_pledge(self):
        """Test resuming a paused pledge."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        pledge = PledgeFactory(contact=contact, status=PledgeStatus.PAUSED)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'/api/v1/pledges/{pledge.id}/resume/')

        assert response.status_code == status.HTTP_200_OK
        pledge.refresh_from_db()
        assert pledge.status == PledgeStatus.ACTIVE

    def test_cancel_pledge(self):
        """Test cancelling a pledge."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        pledge = PledgeFactory(contact=contact, status=PledgeStatus.ACTIVE)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'/api/v1/pledges/{pledge.id}/cancel/')

        assert response.status_code == status.HTTP_200_OK
        pledge.refresh_from_db()
        assert pledge.status == PledgeStatus.CANCELLED


@pytest.mark.django_db
class TestLatePledgesView:
    """Tests for late pledges endpoint."""

    def test_list_late_pledges(self):
        """Test listing late pledges."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)

        # Create one late pledge
        late_pledge = PledgeFactory(contact=contact, is_late=True)

        # Create one on-time pledge
        PledgeFactory(contact=contact, is_late=False)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/pledges/late/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == str(late_pledge.id)
