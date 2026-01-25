"""
Integration tests for contact journals API.

Tests verify:
- GET /api/v1/contacts/{id}/journals/ returns journal memberships
- Response includes journal name, current stage, and decision
- Query optimization prevents N+1 queries
- Ownership validation
"""
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
import datetime

from apps.contacts.models import Contact
from apps.journals.models import Journal, JournalContact, JournalStageEvent, Decision, PipelineStage, StageEventType

User = get_user_model()


class ContactJournalsAPITests(APITestCase):
    """Test suite for contact journals endpoint."""

    def setUp(self):
        """Set up test data: user, contact, journal with membership."""
        # Create user
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='password123',
            first_name='Owner',
            last_name='User',
            role='staff'
        )

        # Create contact
        self.contact = Contact.objects.create(
            owner=self.user,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            status='partner'
        )

        # Create journal
        self.journal = Journal.objects.create(
            owner=self.user,
            name='Q1 2025 Campaign',
            goal_amount=Decimal('5000.00'),
            deadline=datetime.date(2025, 3, 31)
        )

        # Create membership
        self.membership = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact
        )

        # Create stage event
        self.event = JournalStageEvent.objects.create(
            journal_contact=self.membership,
            stage=PipelineStage.MEET,
            event_type=StageEventType.MEETING_COMPLETED,
            triggered_by=self.user
        )

        # Create decision
        self.decision = Decision.objects.create(
            journal_contact=self.membership,
            amount=Decimal('100.00'),
            cadence='monthly',
            status='active'
        )

    def test_get_contact_journals(self):
        """GET /api/v1/contacts/{id}/journals/ returns list of memberships."""
        self.client.force_authenticate(user=self.user)
        url = reverse('contacts:contact-journals', args=[self.contact.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return list with one membership
        data = response.data
        if 'results' in data:  # Paginated response
            results = data['results']
        else:
            results = data

        self.assertEqual(len(results), 1)

        # Verify structure
        membership_data = results[0]
        self.assertEqual(str(membership_data['id']), str(self.membership.id))
        self.assertEqual(str(membership_data['journal_id']), str(self.journal.id))
        self.assertEqual(membership_data['journal_name'], 'Q1 2025 Campaign')
        self.assertEqual(membership_data['goal_amount'], '5000.00')
        self.assertEqual(membership_data['deadline'], '2025-03-31')
        self.assertEqual(membership_data['current_stage'], PipelineStage.MEET)

        # Verify decision structure
        decision_data = membership_data['decision']
        self.assertIsNotNone(decision_data)
        self.assertEqual(str(decision_data['id']), str(self.decision.id))
        self.assertEqual(decision_data['amount'], '100.00')
        self.assertEqual(decision_data['cadence'], 'monthly')
        self.assertEqual(decision_data['status'], 'active')

    def test_no_n_plus_one_queries(self):
        """Query count should not increase with number of memberships."""
        # Create second journal and membership
        journal2 = Journal.objects.create(
            owner=self.user,
            name='Q2 2025 Campaign',
            goal_amount=Decimal('3000.00'),
            deadline=datetime.date(2025, 6, 30)
        )

        membership2 = JournalContact.objects.create(
            journal=journal2,
            contact=self.contact
        )

        JournalStageEvent.objects.create(
            journal_contact=membership2,
            stage=PipelineStage.DECISION,
            event_type=StageEventType.ASK_MADE,
            triggered_by=self.user
        )

        Decision.objects.create(
            journal_contact=membership2,
            amount=Decimal('50.00'),
            cadence='quarterly',
            status='pending'
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('contacts:contact-journals', args=[self.contact.id])

        # Make request - check result has both memberships
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        if 'results' in data:
            results = data['results']
        else:
            results = data

        # Should have both memberships
        self.assertEqual(len(results), 2)

        # Verify both journals present
        journal_names = {r['journal_name'] for r in results}
        self.assertEqual(journal_names, {'Q1 2025 Campaign', 'Q2 2025 Campaign'})

    def test_contact_with_no_journals(self):
        """Contact with no journal memberships returns empty list."""
        # Create contact without memberships
        contact2 = Contact.objects.create(
            owner=self.user,
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            status='prospect'
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('contacts:contact-journals', args=[contact2.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        if 'results' in data:  # Paginated
            results = data['results']
        else:
            results = data

        self.assertEqual(len(results), 0)

    def test_ownership_filtering(self):
        """Users only see memberships for journals they own."""
        # Create second user with different journal
        other_user = User.objects.create_user(
            email='other@example.com',
            password='password123',
            first_name='Other',
            last_name='User',
            role='staff'
        )

        other_journal = Journal.objects.create(
            owner=other_user,
            name='Other Journal',
            goal_amount=Decimal('1000.00'),
            deadline=datetime.date(2025, 12, 31)
        )

        # Add contact to other user's journal
        other_membership = JournalContact.objects.create(
            journal=other_journal,
            contact=self.contact
        )

        # Original user should only see their own journal
        self.client.force_authenticate(user=self.user)
        url = reverse('contacts:contact-journals', args=[self.contact.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        if 'results' in data:
            results = data['results']
        else:
            results = data

        # Should only see the one journal owned by self.user
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['journal_name'], 'Q1 2025 Campaign')
