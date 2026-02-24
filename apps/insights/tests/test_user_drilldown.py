"""
Tests for user drilldown endpoint (Phase 18).
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.models import Contact
from apps.gifts.models import Gift
from apps.journals.models import Journal, JournalContact, Decision, JournalStageEvent, PipelineStage
from apps.users.models import User


class UserDrilldownViewTest(TestCase):
    """Test the user drilldown endpoint."""

    def setUp(self):
        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin',
            first_name='Admin',
            last_name='User',
        )

        # Create staff user (missionary)
        self.missionary = User.objects.create_user(
            email='missionary@test.com',
            password='testpass123',
            role='staff',
            first_name='Missionary',
            last_name='Smith',
        )

        # Create non-admin staff user
        self.staff = User.objects.create_user(
            email='staff@test.com',
            password='testpass123',
            role='staff',
            first_name='Staff',
            last_name='Member',
        )

        # Create contacts owned by missionary
        self.contact1 = Contact.objects.create(
            owner=self.missionary,
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            status='active',
        )
        self.contact2 = Contact.objects.create(
            owner=self.missionary,
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            status='active',
        )
        self.contact3 = Contact.objects.create(
            owner=self.missionary,
            first_name='Bob',
            last_name='Johnson',
            email='bob@test.com',
            status='active',
        )

        # Create journals
        self.journal1 = Journal.objects.create(
            owner=self.missionary,
            name='Journal 1',
            goal_amount=Decimal('50000.00'),
            is_archived=False,
        )
        self.journal2 = Journal.objects.create(
            owner=self.missionary,
            name='Journal 2',
            goal_amount=Decimal('30000.00'),
            is_archived=False,
        )
        self.journal3 = Journal.objects.create(
            owner=self.missionary,
            name='Journal 3 (archived)',
            goal_amount=Decimal('20000.00'),
            is_archived=True,
        )

        # Add contacts to journals
        self.jc1 = JournalContact.objects.create(journal=self.journal1, contact=self.contact1)
        self.jc2 = JournalContact.objects.create(journal=self.journal1, contact=self.contact2)
        self.jc3 = JournalContact.objects.create(journal=self.journal2, contact=self.contact3)

        # Create stage events (for stalled calculation)
        # contact1: recent activity (not stalled)
        JournalStageEvent.objects.create(
            journal_contact=self.jc1,
            stage=PipelineStage.CONTACT,
            created_at=timezone.now() - timedelta(days=5),
        )
        # contact2: old activity (stalled)
        JournalStageEvent.objects.create(
            journal_contact=self.jc2,
            stage=PipelineStage.MEET,
            created_at=timezone.now() - timedelta(days=20),
        )
        # contact3: no activity (stalled)

        # Create decisions
        Decision.objects.create(
            journal_contact=self.jc1,
            amount=Decimal('100.00'),
            cadence='monthly',
            status='active',
        )
        Decision.objects.create(
            journal_contact=self.jc2,
            amount=Decimal('50.00'),
            cadence='monthly',
            status='active',
        )

        # Create gifts
        Gift.objects.create(
            donor_contact=self.contact1,
            amount_cents=10000,  # $100.00
            gift_date=timezone.now().date(),
        )
        Gift.objects.create(
            donor_contact=self.contact2,
            amount_cents=5000,  # $50.00
            gift_date=timezone.now().date(),
        )

        self.client = APIClient()
        self.url = reverse('insights:admin-user-drilldown')

    def test_admin_can_access_endpoint(self):
        """Admin user can access user drilldown endpoint."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'user_id': str(self.missionary.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_gets_403(self):
        """Non-admin user gets 403 Forbidden."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url, {'user_id': str(self.missionary.id)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_id_parameter_required(self):
        """User_id parameter is required."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_returns_correct_stats(self):
        """Returns correct stats for the user."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'user_id': str(self.missionary.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check user info
        self.assertEqual(response.data['user']['id'], str(self.missionary.id))
        self.assertEqual(response.data['user']['name'], 'Missionary Smith')
        self.assertEqual(response.data['user']['email'], 'missionary@test.com')
        self.assertEqual(response.data['user']['role'], 'staff')

        # Check stats
        self.assertEqual(response.data['stats']['total_contacts'], 3)
        self.assertEqual(response.data['stats']['active_journals'], 2)
        self.assertEqual(response.data['stats']['decisions_logged'], 2)
        self.assertEqual(response.data['stats']['conversion_rate'], 66.7)  # 2/3 * 100
        self.assertEqual(response.data['stats']['total_donations'], 15000.0)  # 15000 cents ($150.00)
        self.assertEqual(response.data['stats']['donation_count'], 2)

    def test_returns_stalled_contact_count(self):
        """Returns correct stalled contact count."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'user_id': str(self.missionary.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 1 stalled contact: contact2 (20 days old activity)
        # contact3 has no activity but was just added, so it's not >14 days stalled yet
        # (The stalled logic uses journal_membership_date as fallback, which is recent)
        self.assertEqual(response.data['stats']['stalled_contacts'], 1)

    def test_returns_recent_journals(self):
        """Returns recent journals with progress indicators."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'user_id': str(self.missionary.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return 2 non-archived journals
        self.assertEqual(len(response.data['journals']), 2)

        # Check journal structure
        journal = response.data['journals'][0]
        self.assertIn('id', journal)
        self.assertIn('name', journal)
        self.assertIn('member_count', journal)
        self.assertIn('decision_count', journal)
        self.assertIn('active_member_count', journal)
        self.assertIn('created_at', journal)

        # Check journal1 has 2 members, 2 decisions, 2 active
        journal1_data = next(j for j in response.data['journals'] if j['name'] == 'Journal 1')
        self.assertEqual(journal1_data['member_count'], 2)
        self.assertEqual(journal1_data['decision_count'], 2)
        self.assertEqual(journal1_data['active_member_count'], 2)

        # Check journal2 has 1 member, 0 decisions, 0 active
        journal2_data = next(j for j in response.data['journals'] if j['name'] == 'Journal 2')
        self.assertEqual(journal2_data['member_count'], 1)
        self.assertEqual(journal2_data['decision_count'], 0)
        self.assertEqual(journal2_data['active_member_count'], 0)

    def test_returns_404_for_nonexistent_user(self):
        """Returns 404 for non-existent user."""
        self.client.force_authenticate(user=self.admin)
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = self.client.get(self.url, {'user_id': fake_uuid})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)
