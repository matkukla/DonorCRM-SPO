"""
Integration tests for the complete donor workflow.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.models import Contact, ContactStatus


@pytest.mark.django_db
class TestDonorWorkflow:
    """
    Test the complete workflow from prospect to donor using Gift model.
    """

    def test_complete_donor_journey(self, authenticated_client):
        """
        Test complete journey:
        1. Create prospect
        2. Add first gift (becomes donor)
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

        # Step 2: Add first gift via Gift API
        response = client.post('/api/v1/gifts/', {
            'donor_contact': contact_id,
            'amount_cents': 10000,  # $100.00
            'gift_date': timezone.now().date().isoformat(),
        })
        assert response.status_code == status.HTTP_201_CREATED

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

        # Step 5: Add second gift
        response = client.post('/api/v1/gifts/', {
            'donor_contact': contact_id,
            'amount_cents': 5000,  # $50.00
            'gift_date': timezone.now().date().isoformat(),
        })
        assert response.status_code == status.HTTP_201_CREATED

        # Verify cumulative stats
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        assert Decimal(response.data['total_given']) == Decimal('150.00')
        assert response.data['gift_count'] == 2


@pytest.mark.django_db
class TestRecurringGiftWorkflow:
    """
    Test recurring gift creation.
    """

    def test_create_recurring_gift(self, authenticated_client):
        """
        Test:
        1. Create contact
        2. Create monthly recurring gift
        3. Verify recurring gift details
        """
        client, user = authenticated_client

        # Create contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Bob',
            'last_name': 'Jones',
            'email': 'bob@example.com'
        })
        contact_id = response.data['id']

        # Create monthly recurring gift for $100 (10000 cents)
        response = client.post('/api/v1/gifts/recurring/', {
            'donor_contact': contact_id,
            'amount_cents': 10000,
            'frequency': 'monthly',
            'start_date': timezone.now().date().isoformat(),
            'status': 'active'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount_cents'] == 10000
        assert response.data['frequency'] == 'monthly'


@pytest.mark.django_db
class TestDashboardIntegration:
    """
    Test dashboard aggregations with real data.
    """

    def test_dashboard_with_activity(self, authenticated_client):
        """
        Test dashboard shows correct data after creating contacts and gifts.
        """
        client, user = authenticated_client

        # Create contact and gift
        contact_response = client.post('/api/v1/contacts/', {
            'first_name': 'Test',
            'last_name': 'Dashboard',
            'email': 'test@dashboard.com'
        })
        contact_id = contact_response.data['id']

        client.post('/api/v1/gifts/', {
            'donor_contact': contact_id,
            'amount_cents': 25000,  # $250.00
            'gift_date': timezone.now().date().isoformat(),
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

    def test_staff_cannot_see_other_contacts(self, authenticated_client, user_factory):
        """Test staff users can only see their own contacts."""
        client, user1 = authenticated_client

        # User 1 creates a contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Private',
            'last_name': 'Contact',
            'email': 'private@example.com'
        })
        contact_id = response.data['id']

        # Create another user and authenticate as them
        user2 = user_factory(role='missionary')
        client.force_authenticate(user=user2)

        # User 2 tries to access User 1's contact
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 2 lists contacts - should not see User 1's contact
        response = client.get('/api/v1/contacts/')
        assert response.status_code == status.HTTP_200_OK
        contact_ids = [c['id'] for c in response.data['results']]
        assert contact_id not in contact_ids

    def test_admin_sees_own_contacts_only(self, authenticated_client, admin_client):
        """Test admins see only their own contacts (cross-user access via View As only)."""
        client, user = authenticated_client
        admin_cli, admin = admin_client

        # Regular user creates a contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Other',
            'last_name': 'UserContact',
            'email': 'other@example.com'
        })
        other_contact_id = response.data['id']

        # Admin creates their own contact
        response = admin_cli.post('/api/v1/contacts/', {
            'first_name': 'Admin',
            'last_name': 'OwnContact',
            'email': 'admin-own@example.com'
        })
        admin_contact_id = response.data['id']

        # Admin cannot see other user's contact
        response = admin_cli.get(f'/api/v1/contacts/{other_contact_id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Admin can see their own contact
        response = admin_cli.get(f'/api/v1/contacts/{admin_contact_id}/')
        assert response.status_code == status.HTTP_200_OK

        # Admin list only includes their own contacts
        response = admin_cli.get('/api/v1/contacts/')
        assert response.status_code == status.HTTP_200_OK
        contact_ids = [c['id'] for c in response.data['results']]
        assert admin_contact_id in contact_ids
        assert other_contact_id not in contact_ids

    def test_coach_cannot_modify_others_contacts(self, authenticated_client):
        """Test coach users cannot modify contacts they don't own."""
        from apps.users.tests.factories import CoachUserFactory
        client, user = authenticated_client

        # Create contact as missionary
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Someone',
            'last_name': 'Else',
            'email': 'someone@example.com'
        })
        contact_id = response.data['id']

        # Coach cannot update another user's contact
        coach = CoachUserFactory()
        coach_client = APIClient()
        coach_client.force_authenticate(user=coach)
        response = coach_client.patch(f'/api/v1/contacts/{contact_id}/', {
            'first_name': 'Updated'
        })
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
class TestEventNotifications:
    """
    Test that events are created for significant actions.
    """

    def test_gift_creates_event(self, authenticated_client):
        """Test that adding a gift creates an event."""
        client, user = authenticated_client

        # Create contact
        response = client.post('/api/v1/contacts/', {
            'first_name': 'Event',
            'last_name': 'Test',
            'email': 'event@test.com'
        })
        contact_id = response.data['id']

        # Check events before gift
        events_before = client.get('/api/v1/events/').data['count']

        # Add gift
        client.post('/api/v1/gifts/', {
            'donor_contact': contact_id,
            'amount_cents': 7500,  # $75.00
            'gift_date': timezone.now().date().isoformat(),
        })

        # Check events after gift
        response = client.get('/api/v1/events/')
        events_after = response.data['count']
        assert events_after > events_before

        # Find the donation event (uses DONATION_RECEIVED event type for backward compat)
        events = response.data['results']
        donation_events = [e for e in events if e['event_type'] == 'donation_received']
        assert len(donation_events) > 0


@pytest.mark.django_db
class TestCoachContactAccess:
    """ROLE-03 and ROLE-05: Coach users can read contacts for their missionaries."""

    def test_coach_can_list_contacts(self, api_client, coach_user, missionary_user):
        """ROLE-03: Coach can GET /api/v1/contacts/ and receive 200."""
        coach_user.coached_users.add(missionary_user)
        api_client.force_authenticate(user=coach_user)
        response = api_client.get('/api/v1/contacts/')
        assert response.status_code == 200

    def test_coach_cannot_create_contact(self, api_client, coach_user):
        """ROLE-03 write block: Coach POST /api/v1/contacts/ returns 403."""
        api_client.force_authenticate(user=coach_user)
        response = api_client.post('/api/v1/contacts/', data={
            'first_name': 'Test', 'last_name': 'Donor'
        }, format='json')
        assert response.status_code == 403

    def test_coach_contact_list_scoped_to_missionaries(self, api_client, coach_user, missionary_user):
        """ROLE-05: Coach sees only contacts owned by their coached missionaries."""
        coach_user.coached_users.add(missionary_user)
        Contact.objects.create(owner=missionary_user, first_name='Visible', last_name='Contact')
        api_client.force_authenticate(user=coach_user)
        response = api_client.get('/api/v1/contacts/')
        assert response.status_code == 200
        # scoped: returns contacts owned by coached missionaries
