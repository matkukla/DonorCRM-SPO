"""
Integration tests for the complete donor workflow.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.contacts.models import ContactStatus
from apps.donations.models import DonationType


@pytest.mark.django_db
class TestDonorWorkflow:
    """
    Test the complete workflow from prospect to donor.
    """

    def test_complete_donor_journey(self, authenticated_client):
        """
        Test complete journey:
        1. Create prospect
        2. Add first donation (becomes donor)
        3. Stats update automatically
        4. Thank-you tracking
        """
        client, user = authenticated_client

        # Step 1: Create a prospect
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'phone': '555-1234',
            'status': ContactStatus.PROSPECT
        })
        assert response.status_code == status.HTTP_201_CREATED
        contact_id = response.data['id']
        assert response.data['status'] == ContactStatus.PROSPECT
        assert response.data['total_given'] == '0.00'
        assert response.data['gift_count'] == 0

        # Step 2: Add first donation
        response = client.post('/api/v1/donations/', {
            'contact': contact_id,
            'amount': '100.00',
            'date': timezone.now().date().isoformat(),
            'donation_type': DonationType.ONE_TIME,
            'payment_method': 'check'
        })
        assert response.status_code == status.HTTP_201_CREATED
        donation_id = response.data['id']

        # Step 3: Verify contact stats updated
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == ContactStatus.DONOR
        assert Decimal(response.data['total_given']) == Decimal('100.00')
        assert response.data['gift_count'] == 1
        assert response.data['needs_thank_you'] is True

        # Step 4: Mark as thanked
        response = client.post(f'/api/v1/contacts/{contact_id}/thank/')
        assert response.status_code == status.HTTP_200_OK

        response = client.get(f'/api/v1/contacts/{contact_id}/')
        assert response.data['needs_thank_you'] is False

        # Step 5: Add second donation
        response = client.post('/api/v1/donations/', {
            'contact': contact_id,
            'amount': '50.00',
            'date': timezone.now().date().isoformat(),
            'donation_type': DonationType.ONE_TIME,
            'payment_method': 'credit_card'
        })
        assert response.status_code == status.HTTP_201_CREATED

        # Verify cumulative stats
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        assert Decimal(response.data['total_given']) == Decimal('150.00')
        assert response.data['gift_count'] == 2


@pytest.mark.django_db
class TestPledgeWorkflow:
    """
    Test pledge creation and fulfillment tracking.
    """

    def test_pledge_with_donations(self, authenticated_client):
        """
        Test:
        1. Create contact
        2. Create monthly pledge
        3. Add donations to fulfill pledge
        4. Verify pledge tracking updates
        """
        client, user = authenticated_client

        # Create contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Bob',
            'last_name': 'Jones',
            'email': 'bob@example.com'
        })
        contact_id = response.data['id']

        # Create monthly pledge for $100
        response = client.post('/api/v1/pledges/', {
            'contact': contact_id,
            'amount': '100.00',
            'frequency': 'monthly',
            'start_date': timezone.now().date().isoformat(),
            'status': 'active'
        })
        assert response.status_code == status.HTTP_201_CREATED
        pledge_id = response.data['id']
        assert response.data['monthly_equivalent'] == '100.00'

        # Add donation to fulfill this month's pledge
        response = client.post('/api/v1/donations/', {
            'contact': contact_id,
            'pledge': pledge_id,
            'amount': '100.00',
            'date': timezone.now().date().isoformat(),
            'donation_type': DonationType.RECURRING
        })
        assert response.status_code == status.HTTP_201_CREATED

        print("Donation response.data:", response.data)
        print("Donation raw content:", response.content.decode())

        # Verify pledge updated
        response = client.get(f'/api/v1/pledges/{pledge_id}/')
        assert Decimal(response.data['total_received']) == Decimal('100.00')
        assert response.data['is_late'] is False


@pytest.mark.django_db
class TestDashboardIntegration:
    """
    Test dashboard aggregations with real data.
    """

    def test_dashboard_with_activity(self, authenticated_client):
        """
        Test dashboard shows correct data after creating contacts and donations.
        """
        client, user = authenticated_client

        # Create contact and donation
        contact_response = client.post('/api/v1/contacts/', {
            'first_name': 'Test',
            'last_name': 'Dashboard',
            'email': 'test@dashboard.com'
        })
        contact_id = contact_response.data['id']

        client.post('/api/v1/donations/', {
            'contact': contact_id,
            'amount': '250.00',
            'date': timezone.now().date().isoformat(),
            'donation_type': DonationType.ONE_TIME
        })

        # Get dashboard
        response = client.get('/api/v1/dashboard/')
        assert response.status_code == status.HTTP_200_OK

        # Verify thank-you queue
        response = client.get('/api/v1/dashboard/thank-you-queue/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

        # Verify recent gifts
        response = client.get('/api/v1/dashboard/recent-gifts/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


@pytest.mark.django_db
class TestPermissionBoundaries:
    """
    Test that permission boundaries are enforced.
    """

    def test_fundraiser_cannot_see_other_contacts(self, authenticated_client, user_factory):
        """Test fundraisers can only see their own contacts."""
        client, user1 = authenticated_client

        # User 1 creates a contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Private',
            'last_name': 'Contact',
            'email': 'private@example.com'
        })
        contact_id = response.data['id']

        # Create another user and authenticate as them
        user2 = user_factory(role='fundraiser')
        client.force_authenticate(user=user2)

        # User 2 tries to access User 1's contact
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 lists contacts - should not see User 1's contact
        response = client.get('/api/v1/contacts/')
        assert response.status_code == status.HTTP_200_OK
        contact_ids = [c['id'] for c in response.data['results']]
        assert contact_id not in contact_ids

    def test_admin_sees_all_contacts(self, authenticated_client, admin_client):
        """Test admins can see all contacts regardless of owner."""
        client, user = authenticated_client
        admin_cli, admin = admin_client

        # Regular user creates a contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Admin',
            'last_name': 'Visible',
            'email': 'visible@example.com'
        })
        contact_id = response.data['id']

        # Admin can see it
        response = admin_cli.get(f'/api/v1/contacts/{contact_id}/')
        assert response.status_code == status.HTTP_200_OK

        # Admin can list all contacts
        response = admin_cli.get('/api/v1/contacts/')
        assert response.status_code == status.HTTP_200_OK
        contact_ids = [c['id'] for c in response.data['results']]
        assert contact_id in contact_ids

    def test_finance_can_read_but_not_modify_contacts(self, authenticated_client, finance_client):
        """Test finance users can read contacts but not modify them."""
        client, user = authenticated_client
        finance_cli, finance_user = finance_client

        # Create contact as fundraiser
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Finance',
            'last_name': 'Readonly',
            'email': 'finance@example.com'
        })
        contact_id = response.data['id']

        # Finance can read
        response = finance_cli.get(f'/api/v1/contacts/{contact_id}/')
        assert response.status_code == status.HTTP_200_OK

        # Finance cannot update
        response = finance_cli.patch(f'/api/v1/contacts/{contact_id}/', {
            'first_name': 'Updated'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestEventNotifications:
    """
    Test that events are created for significant actions.
    """

    def test_donation_creates_event(self, authenticated_client):
        """Test that adding a donation creates an event."""
        client, user = authenticated_client

        # Create contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Event',
            'last_name': 'Test',
            'email': 'event@test.com'
        })
        contact_id = response.data['id']

        # Check events before donation
        events_before = client.get('/api/v1/events/').data['count']

        # Add donation
        client.post('/api/v1/donations/', {
            'contact': contact_id,
            'amount': '75.00',
            'date': timezone.now().date().isoformat(),
            'donation_type': DonationType.ONE_TIME
        })

        # Check events after donation
        response = client.get('/api/v1/events/')
        events_after = response.data['count']
        assert events_after > events_before

        # Find the donation event
        events = response.data['results']
        donation_events = [e for e in events if e['event_type'] == 'donation_received']
        assert len(donation_events) > 0
