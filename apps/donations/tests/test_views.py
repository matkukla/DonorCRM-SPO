"""
Tests for Donation API views.
"""
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.tests.factories import ContactFactory
from apps.donations.models import Donation
from apps.donations.tests.factories import DonationFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestDonationListCreateView:
    """Tests for donation list and create endpoints."""

    def test_list_donations_authenticated(self):
        """Test listing donations for authenticated user."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        DonationFactory.create_batch(3, contact=contact)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/donations/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_list_donations_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/v1/donations/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_donation(self):
        """Test creating a donation."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            'contact': str(contact.id),
            'amount': '100.00',
            'date': str(timezone.now().date()),
            'donation_type': 'one_time',
            'payment_method': 'check'
        }

        response = client.post('/api/v1/donations/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount'] == '100.00'
        assert 'id' in response.data

    def test_staff_only_sees_own_contacts_donations(self):
        """Test that staff only sees donations from their contacts."""
        user1 = UserFactory(role='staff')
        user2 = UserFactory(role='staff')
        contact1 = ContactFactory(owner=user1)
        contact2 = ContactFactory(owner=user2)
        DonationFactory.create_batch(2, contact=contact1)
        DonationFactory.create_batch(3, contact=contact2)

        client = APIClient()
        client.force_authenticate(user=user1)

        response = client.get('/api/v1/donations/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2


@pytest.mark.django_db
class TestDonationDetailView:
    """Tests for donation detail endpoint."""

    def test_get_donation_detail(self):
        """Test getting donation detail."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        donation = DonationFactory(contact=contact, amount=Decimal('250.00'))

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f'/api/v1/donations/{donation.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['amount'] == '250.00'

    def test_update_donation(self):
        """Test updating a donation."""
        user = UserFactory(role='admin')
        contact = ContactFactory(owner=user)
        donation = DonationFactory(contact=contact, amount=Decimal('100.00'))

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch(
            f'/api/v1/donations/{donation.id}/',
            {'notes': 'Updated notes'}
        )

        assert response.status_code == status.HTTP_200_OK
        donation.refresh_from_db()
        assert donation.notes == 'Updated notes'

    def test_delete_donation_admin(self):
        """Test admin can delete donation."""
        user = UserFactory(role='admin')
        contact = ContactFactory(owner=user)
        donation = DonationFactory(contact=contact)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(f'/api/v1/donations/{donation.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Donation.objects.filter(id=donation.id).exists()


@pytest.mark.django_db
class TestDonationThankView:
    """Tests for marking donations as thanked."""

    def test_mark_donation_thanked(self):
        """Test marking a donation as thanked."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        donation = DonationFactory(contact=contact, thanked=False)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'/api/v1/donations/{donation.id}/thank/')

        assert response.status_code == status.HTTP_200_OK
        donation.refresh_from_db()
        assert donation.thanked is True
        assert donation.thanked_by == user


@pytest.mark.django_db
class TestDonationSummaryView:
    """Tests for donation summary endpoint."""

    def test_donation_summary(self):
        """Test getting donation summary statistics."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)
        DonationFactory(contact=contact, amount=Decimal('100.00'))
        DonationFactory(contact=contact, amount=Decimal('200.00'))

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/donations/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_amount' in response.data
        assert 'donation_count' in response.data
