"""
Integration tests for NextStep API.

Tests verify:
- NextStep CRUD operations (create, list, update, delete)
- Mark complete/uncomplete with automatic timestamp handling
- Filtering by journal_contact and completed status
- Ownership validation (only owner can access)
- Cross-user protection
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.contacts.models import Contact
from apps.journals.models import Journal, JournalContact, NextStep

User = get_user_model()


class NextStepAPITests(APITestCase):
    """Test suite for NextStep CRUD API endpoints."""

    def setUp(self):
        """Set up test data: two users, journals, contacts, and journal_contacts."""
        # Create two users
        self.user_a = User.objects.create_user(
            email='usera@example.com',
            password='password123',
            first_name='User',
            last_name='A',
            role='staff'
        )
        self.user_b = User.objects.create_user(
            email='userb@example.com',
            password='password123',
            first_name='User',
            last_name='B',
            role='staff'
        )

        # Create journal owned by user_a
        self.journal = Journal.objects.create(
            owner=self.user_a,
            name='Q1 2025 Campaign',
            goal_amount=50000.00
        )

        # Create contacts owned by user_a
        self.contact_a1 = Contact.objects.create(
            owner=self.user_a,
            first_name='Alice',
            last_name='Anderson',
            email='alice.anderson@example.com',
            status='prospect'
        )
        self.contact_a2 = Contact.objects.create(
            owner=self.user_a,
            first_name='Bob',
            last_name='Brown',
            email='bob.brown@example.com',
            status='donor'
        )

        # Create journal_contacts
        self.jc1 = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact_a1
        )
        self.jc2 = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact_a2
        )

        # Create journal and contact for user_b
        self.journal_b = Journal.objects.create(
            owner=self.user_b,
            name='User B Journal',
            goal_amount=30000.00
        )
        self.contact_b = Contact.objects.create(
            owner=self.user_b,
            first_name='Charlie',
            last_name='Clark',
            email='charlie@example.com',
            status='prospect'
        )
        self.jc_b = JournalContact.objects.create(
            journal=self.journal_b,
            contact=self.contact_b
        )

        # Default authentication to user_a
        self.client.force_authenticate(user=self.user_a)

    # Test 1: Create next step

    def test_create_next_step_success(self):
        """Test successfully creating a next step with all fields."""
        url = reverse('journals:nextstep-list')
        data = {
            'journal_contact': str(self.jc1.id),
            'title': 'Send thank you email',
            'notes': 'Follow up on meeting',
            'due_date': '2025-02-15',
            'order': 1
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(str(response.data['journal_contact']), str(self.jc1.id))
        self.assertEqual(response.data['title'], 'Send thank you email')
        self.assertEqual(response.data['notes'], 'Follow up on meeting')
        self.assertEqual(response.data['due_date'], '2025-02-15')
        self.assertEqual(response.data['completed'], False)
        self.assertIsNone(response.data['completed_at'])
        self.assertEqual(NextStep.objects.count(), 1)

    def test_create_next_step_minimal(self):
        """Test creating next step with only required fields."""
        url = reverse('journals:nextstep-list')
        data = {
            'journal_contact': str(self.jc1.id),
            'title': 'Call donor'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Call donor')
        self.assertEqual(response.data['notes'], '')
        self.assertIsNone(response.data['due_date'])
        self.assertEqual(response.data['order'], 0)

    # Test 2: List next steps with filter

    def test_list_next_steps_by_journal_contact(self):
        """Test listing next steps filtered by journal_contact."""
        # Create next steps for both journal_contacts
        NextStep.objects.create(
            journal_contact=self.jc1,
            title='Step for JC1'
        )
        NextStep.objects.create(
            journal_contact=self.jc2,
            title='Step for JC2'
        )

        url = reverse('journals:nextstep-list')
        response = self.client.get(url, {'journal_contact': str(self.jc1.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Step for JC1')

    def test_list_next_steps_by_completed_status(self):
        """Test filtering next steps by completed status."""
        # Create completed and incomplete next steps
        NextStep.objects.create(
            journal_contact=self.jc1,
            title='Incomplete step',
            completed=False
        )
        NextStep.objects.create(
            journal_contact=self.jc1,
            title='Complete step',
            completed=True
        )

        url = reverse('journals:nextstep-list')

        # Filter for incomplete
        response = self.client.get(url, {'completed': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Incomplete step')

        # Filter for complete
        response = self.client.get(url, {'completed': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Complete step')

    # Test 3: Mark complete

    def test_mark_next_step_complete(self):
        """Test marking a next step as complete sets completed_at."""
        next_step = NextStep.objects.create(
            journal_contact=self.jc1,
            title='Send email'
        )

        url = reverse('journals:nextstep-detail', kwargs={'pk': next_step.id})
        response = self.client.patch(url, {'completed': True}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['completed'], True)
        self.assertIsNotNone(response.data['completed_at'])

        # Verify in database
        next_step.refresh_from_db()
        self.assertTrue(next_step.completed)
        self.assertIsNotNone(next_step.completed_at)

    # Test 4: Unmark complete

    def test_unmark_next_step_complete(self):
        """Test unmarking a complete next step clears completed_at."""
        from django.utils import timezone

        next_step = NextStep.objects.create(
            journal_contact=self.jc1,
            title='Send email',
            completed=True,
            completed_at=timezone.now()
        )

        url = reverse('journals:nextstep-detail', kwargs={'pk': next_step.id})
        response = self.client.patch(url, {'completed': False}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['completed'], False)
        self.assertIsNone(response.data['completed_at'])

        # Verify in database
        next_step.refresh_from_db()
        self.assertFalse(next_step.completed)
        self.assertIsNone(next_step.completed_at)

    # Test 5: Delete next step

    def test_delete_next_step(self):
        """Test deleting a next step."""
        next_step = NextStep.objects.create(
            journal_contact=self.jc1,
            title='Send email'
        )

        url = reverse('journals:nextstep-detail', kwargs={'pk': next_step.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(NextStep.objects.count(), 0)

    # Test 6: Ownership enforcement

    def test_cannot_create_next_step_for_other_users_journal_contact(self):
        """Test that user_a cannot create next step for user_b's journal_contact."""
        url = reverse('journals:nextstep-list')
        data = {
            'journal_contact': str(self.jc_b.id),
            'title': 'Try to add to user_b contact'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('journal_contact', response.data)

    # Test 7: Cross-user protection

    def test_cannot_see_other_users_next_steps(self):
        """Test that user_b cannot see user_a's next steps."""
        # Create next step for user_a's journal_contact
        NextStep.objects.create(
            journal_contact=self.jc1,
            title='User A step'
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:nextstep-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # user_b should see 0 next steps (user_a's are filtered out)
        self.assertEqual(response.data['count'], 0)

    def test_cannot_update_other_users_next_step(self):
        """Test that user_b cannot update user_a's next step."""
        # Create next step for user_a's journal_contact
        next_step = NextStep.objects.create(
            journal_contact=self.jc1,
            title='User A step'
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:nextstep-detail', kwargs={'pk': next_step.id})
        response = self.client.patch(url, {'title': 'Hacked'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_delete_other_users_next_step(self):
        """Test that user_b cannot delete user_a's next step."""
        # Create next step for user_a's journal_contact
        next_step = NextStep.objects.create(
            journal_contact=self.jc1,
            title='User A step'
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:nextstep-detail', kwargs={'pk': next_step.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Verify still exists
        self.assertEqual(NextStep.objects.count(), 1)

    # Test 8: Ordering

    def test_next_steps_ordered_by_order_then_created_at(self):
        """Test that next steps are returned in correct order."""
        # Create next steps with different orders
        ns3 = NextStep.objects.create(
            journal_contact=self.jc1,
            title='Third',
            order=3
        )
        ns1 = NextStep.objects.create(
            journal_contact=self.jc1,
            title='First',
            order=1
        )
        ns2 = NextStep.objects.create(
            journal_contact=self.jc1,
            title='Second',
            order=2
        )

        url = reverse('journals:nextstep-list')
        response = self.client.get(url, {'journal_contact': str(self.jc1.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['results'][0]['title'], 'First')
        self.assertEqual(response.data['results'][1]['title'], 'Second')
        self.assertEqual(response.data['results'][2]['title'], 'Third')
