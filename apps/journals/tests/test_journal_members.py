"""
Integration tests for journal membership API.

Tests verify:
- Membership CRUD operations
- Duplicate handling
- Multi-journal membership
- Ownership validation (journal and contact)
- Search by name/email (case-insensitive)
- Filtering by contact status
- Combined search + filter
- Archived journal exclusion
- Journal-specific listing
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.contacts.models import Contact
from apps.journals.models import Journal, JournalContact

User = get_user_model()


class JournalContactTests(APITestCase):
    """Test suite for journal membership API endpoints."""

    def setUp(self):
        """Set up test data: two users, journals, and contacts."""
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

        # Create 3 contacts owned by user_a with varied data for search testing
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
        self.contact_a3 = Contact.objects.create(
            owner=self.user_a,
            first_name='Charlie',
            last_name='Clark',
            email='charlie@testdomain.com',
            status='asked'
        )

        # Create 1 contact owned by user_b
        self.contact_b = Contact.objects.create(
            owner=self.user_b,
            first_name='Diana',
            last_name='Davis',
            email='diana@example.com',
            status='prospect'
        )

        # Default authentication to user_a
        self.client.force_authenticate(user=self.user_a)

    def test_add_contact_to_journal_success(self):
        """Test successfully adding a contact to a journal."""
        url = reverse('journals:journal-member-list')
        data = {
            'journal': str(self.journal.id),
            'contact': str(self.contact_a1.id)
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(str(response.data['journal']), str(self.journal.id))
        self.assertEqual(str(response.data['contact']), str(self.contact_a1.id))
        self.assertEqual(response.data['contact_name'], 'Alice Anderson')
        self.assertEqual(response.data['contact_email'], 'alice.anderson@example.com')
        self.assertIn('created_at', response.data)
        self.assertEqual(JournalContact.objects.count(), 1)

    def test_add_multiple_contacts(self):
        """Test adding multiple contacts to the same journal."""
        url = reverse('journals:journal-member-list')

        # Add first contact
        response1 = self.client.post(url, {
            'journal': str(self.journal.id),
            'contact': str(self.contact_a1.id)
        }, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Add second contact
        response2 = self.client.post(url, {
            'journal': str(self.journal.id),
            'contact': str(self.contact_a2.id)
        }, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Add third contact
        response3 = self.client.post(url, {
            'journal': str(self.journal.id),
            'contact': str(self.contact_a3.id)
        }, format='json')
        self.assertEqual(response3.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            JournalContact.objects.filter(journal=self.journal).count(),
            3
        )

    def test_remove_contact_from_journal(self):
        """Test removing a contact from a journal."""
        # Create membership
        jc = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact_a1
        )

        url = reverse('journals:journal-member-detail', kwargs={'pk': jc.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(JournalContact.objects.count(), 0)

    def test_duplicate_membership_returns_400(self):
        """Test that adding the same contact twice returns 400."""
        url = reverse('journals:journal-member-list')
        data = {
            'journal': str(self.journal.id),
            'contact': str(self.contact_a1.id)
        }

        # First POST should succeed
        response1 = self.client.post(url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second POST should fail with 400
        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        # Could be 'detail' (custom handler) or 'non_field_errors' (DRF default)
        self.assertTrue(
            'detail' in response2.data or 'non_field_errors' in response2.data
        )

    def test_contact_in_multiple_journals(self):
        """Test that a contact can belong to multiple journals."""
        # Create second journal for user_a
        journal2 = Journal.objects.create(
            owner=self.user_a,
            name='Q2 2025 Campaign',
            goal_amount=60000.00
        )

        url = reverse('journals:journal-member-list')

        # Add same contact to first journal
        response1 = self.client.post(url, {
            'journal': str(self.journal.id),
            'contact': str(self.contact_a1.id)
        }, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Add same contact to second journal
        response2 = self.client.post(url, {
            'journal': str(journal2.id),
            'contact': str(self.contact_a1.id)
        }, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Verify contact is in both journals
        self.assertEqual(
            JournalContact.objects.filter(contact=self.contact_a1).count(),
            2
        )

    def test_cannot_add_contact_owned_by_other_user(self):
        """Test that user cannot add a contact they don't own."""
        url = reverse('journals:journal-member-list')
        data = {
            'journal': str(self.journal.id),
            'contact': str(self.contact_b.id)  # Owned by user_b
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contact', response.data)

    def test_cannot_add_to_journal_owned_by_other_user(self):
        """Test that user cannot add contacts to another user's journal."""
        # Create journal owned by user_b
        journal_b = Journal.objects.create(
            owner=self.user_b,
            name='User B Journal',
            goal_amount=30000.00
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:journal-member-list')
        data = {
            'journal': str(self.journal.id),  # Owned by user_a
            'contact': str(self.contact_b.id)
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('journal', response.data)

    def test_cannot_list_other_users_memberships(self):
        """Test that users cannot see memberships from other users' journals."""
        # Create membership for user_a's journal
        JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact_a1
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:journal-member-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_cannot_delete_other_users_membership(self):
        """Test that users cannot delete memberships from other users' journals."""
        # Create membership for user_a's journal
        jc = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact_a1
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:journal-member-detail', kwargs={'pk': jc.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Membership should still exist
        self.assertEqual(JournalContact.objects.count(), 1)

    def test_search_by_first_name(self):
        """Test searching memberships by contact first name."""
        # Add all contacts to journal
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a1)
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a2)
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a3)

        url = reverse('journals:journal-member-list')
        response = self.client.get(url, {
            'journal_id': str(self.journal.id),
            'search': 'Alice'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            str(response.data['results'][0]['contact']),
            str(self.contact_a1.id)
        )

    def test_search_by_email(self):
        """Test searching memberships by contact email."""
        # Add all contacts to journal
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a1)
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a2)
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a3)

        url = reverse('journals:journal-member-list')
        response = self.client.get(url, {
            'journal_id': str(self.journal.id),
            'search': 'testdomain'  # Partial match
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            str(response.data['results'][0]['contact']),
            str(self.contact_a3.id)
        )

    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        # Add contact to journal
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a1)

        url = reverse('journals:journal-member-list')
        response = self.client.get(url, {
            'search': 'ALICE'  # Uppercase
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            str(response.data['results'][0]['contact']),
            str(self.contact_a1.id)
        )

    def test_filter_by_contact_status(self):
        """Test filtering memberships by contact status."""
        # Add contacts with different statuses
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a1)  # prospect
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a2)  # donor
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a3)  # asked

        url = reverse('journals:journal-member-list')
        response = self.client.get(url, {
            'journal_id': str(self.journal.id),
            'contact__status': 'donor'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            str(response.data['results'][0]['contact']),
            str(self.contact_a2.id)
        )
        self.assertEqual(
            response.data['results'][0]['contact_status'],
            'donor'
        )

    def test_filter_and_search_combined(self):
        """Test combining search and filter parameters."""
        # Add contacts
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a1)  # Alice, prospect
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a2)  # Bob, donor
        JournalContact.objects.create(journal=self.journal, contact=self.contact_a3)  # Charlie, asked

        url = reverse('journals:journal-member-list')
        response = self.client.get(url, {
            'journal_id': str(self.journal.id),
            'search': 'a',  # Should match Alice and Charlie
            'contact__status': 'prospect'  # Only Alice is prospect
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            str(response.data['results'][0]['contact']),
            str(self.contact_a1.id)
        )

    def test_archived_journal_memberships_excluded(self):
        """Test that memberships from archived journals are excluded."""
        # Create membership
        JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact_a1
        )

        # Verify membership is listed before archiving
        url = reverse('journals:journal-member-list')
        response = self.client.get(url)
        self.assertEqual(response.data['count'], 1)

        # Archive the journal
        self.journal.archive()

        # Verify membership is not listed after archiving
        response = self.client.get(url)
        self.assertEqual(response.data['count'], 0)

    def test_list_with_journal_id_filter(self):
        """Test filtering memberships by journal_id."""
        # Create second journal
        journal2 = Journal.objects.create(
            owner=self.user_a,
            name='Q2 2025 Campaign',
            goal_amount=60000.00
        )

        # Create memberships in both journals
        jc1 = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact_a1
        )
        jc2 = JournalContact.objects.create(
            journal=journal2,
            contact=self.contact_a2
        )

        url = reverse('journals:journal-member-list')

        # Filter by first journal
        response = self.client.get(url, {'journal_id': str(self.journal.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            str(response.data['results'][0]['journal']),
            str(self.journal.id)
        )

        # Filter by second journal
        response = self.client.get(url, {'journal_id': str(journal2.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            str(response.data['results'][0]['journal']),
            str(journal2.id)
        )
