"""
Tests for date range filtering on admin analytics endpoints.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory
from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory
from apps.journals.models import Journal, JournalContact, Decision, JournalStageEvent, PipelineStage
from apps.events.models import Event


@pytest.mark.django_db
class TestDashboardOverviewDateFiltering:
    """Tests for date filtering on /api/v1/insights/admin/dashboard-overview/"""

    def test_date_from_filters_contacts(self, admin_client):
        """Create contacts on different dates, verify date_from filters correctly."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')

        # Create old contact (10 days ago)
        old_date = timezone.now() - timedelta(days=10)
        old_contact = ContactFactory(owner=staff)
        old_contact.created_at = old_date
        old_contact.save()

        # Create new contact (2 days ago)
        new_date = timezone.now() - timedelta(days=2)
        new_contact = ContactFactory(owner=staff)
        new_contact.created_at = new_date
        new_contact.save()

        # Query with date_from=5 days ago (should only count new contact)
        date_from = (timezone.now() - timedelta(days=5)).date().isoformat()
        response = client.get(f'/api/v1/insights/admin/dashboard-overview/?date_from={date_from}')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_contacts'] == 1

    def test_date_to_filters_contacts(self, admin_client):
        """Create contacts on different dates, verify date_to filters correctly."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')

        # Create old contact (10 days ago)
        old_date = timezone.now() - timedelta(days=10)
        old_contact = ContactFactory(owner=staff)
        old_contact.created_at = old_date
        old_contact.save()

        # Create new contact (2 days ago)
        new_date = timezone.now() - timedelta(days=2)
        new_contact = ContactFactory(owner=staff)
        new_contact.created_at = new_date
        new_contact.save()

        # Query with date_to=5 days ago (should only count old contact)
        date_to = (timezone.now() - timedelta(days=5)).date().isoformat()
        response = client.get(f'/api/v1/insights/admin/dashboard-overview/?date_to={date_to}')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_contacts'] == 1

    def test_date_range_filters_donations(self, admin_client):
        """Create gifts on different dates, verify date range filters correctly."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')
        contact = ContactFactory(owner=staff)

        # Create old gift (20 days ago)
        old_date = date.today() - timedelta(days=20)
        GiftFactory(donor_contact=contact, amount_cents=10000, gift_date=old_date)

        # Create new gift (5 days ago)
        new_date = date.today() - timedelta(days=5)
        GiftFactory(donor_contact=contact, amount_cents=20000, gift_date=new_date)

        # Query with date_from=10 days ago (should only count new gift)
        date_from = (date.today() - timedelta(days=10)).isoformat()
        response = client.get(f'/api/v1/insights/admin/dashboard-overview/?date_from={date_from}')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['donations_12m']['total_count'] == 1
        assert response.data['donations_12m']['total_amount'] == 200.0

    def test_invalid_date_format_returns_400(self, admin_client):
        """Send invalid date format, verify 400 error."""
        client, admin_user = admin_client
        response = client.get('/api/v1/insights/admin/dashboard-overview/?date_from=invalid-date')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in response.data
        assert 'date_from' in response.data['detail']

    def test_date_from_without_date_to_works(self, admin_client):
        """Send only date_from, verify it works (open-ended range)."""
        client, admin_user = admin_client
        date_from = (timezone.now() - timedelta(days=30)).date().isoformat()
        response = client.get(f'/api/v1/insights/admin/dashboard-overview/?date_from={date_from}')
        assert response.status_code == status.HTTP_200_OK
        assert 'total_contacts' in response.data

    def test_date_to_without_date_from_works(self, admin_client):
        """Send only date_to, verify it works."""
        client, admin_user = admin_client
        date_to = timezone.now().date().isoformat()
        response = client.get(f'/api/v1/insights/admin/dashboard-overview/?date_to={date_to}')
        assert response.status_code == status.HTTP_200_OK
        assert 'total_contacts' in response.data


@pytest.mark.django_db
class TestStalledContactsDateFiltering:
    """Tests for date filtering on /api/v1/insights/admin/stalled-contacts/"""

    def test_date_to_affects_stalled_calculation(self, admin_client):
        """Verify that date_to is used as 'now' for stalled calculation."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')
        contact = ContactFactory(owner=staff)

        # Create journal and add contact
        journal = Journal.objects.create(
            name='Test Journal',
            owner=staff,
            goal_amount=Decimal('5000.00'),
        )
        jc = JournalContact.objects.create(journal=journal, contact=contact)

        # Create stage event 10 days ago
        event_date = timezone.now() - timedelta(days=10)
        stage_event = JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.CONTACT.value,
        )
        stage_event.created_at = event_date
        stage_event.save()

        # Query with date_to=5 days ago (10 days - 5 days = 5 days old, not stalled yet)
        date_to = (timezone.now() - timedelta(days=5)).date().isoformat()
        response = client.get(f'/api/v1/insights/admin/stalled-contacts/?date_to={date_to}')
        assert response.status_code == status.HTTP_200_OK
        # With cutoff at 14 days and event 5 days old relative to date_to, shouldn't be stalled
        assert response.data['total_count'] == 0

    def test_invalid_date_returns_400(self, admin_client):
        """Send invalid date format, verify 400 error."""
        client, admin_user = admin_client
        response = client.get('/api/v1/insights/admin/stalled-contacts/?date_from=bad-date')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'detail' in response.data


@pytest.mark.django_db
class TestTeamActivityDateFiltering:
    """Tests for date filtering on /api/v1/insights/admin/team-activity/"""

    def test_date_range_filters_events(self, admin_client):
        """Create events on different dates, verify date range filters correctly."""
        client, admin_user = admin_client
        staff = UserFactory(role='missionary')

        # Create old event (20 days ago)
        old_date = timezone.now() - timedelta(days=20)
        old_event = Event.objects.create(
            user=staff,
            event_type='journal_created',
            title='Old Event',
            severity='info',
        )
        old_event.created_at = old_date
        old_event.save()

        # Create new event (5 days ago)
        new_date = timezone.now() - timedelta(days=5)
        new_event = Event.objects.create(
            user=staff,
            event_type='journal_created',
            title='New Event',
            severity='info',
        )
        new_event.created_at = new_date
        new_event.save()

        # Query with date_from=10 days ago (should only show new event)
        date_from = (timezone.now() - timedelta(days=10)).date().isoformat()
        response = client.get(f'/api/v1/insights/admin/team-activity/?date_from={date_from}')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['activities']) == 1
        assert response.data['activities'][0]['title'] == 'New Event'


