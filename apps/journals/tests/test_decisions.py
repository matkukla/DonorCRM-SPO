"""
Integration tests for decision API.

Tests verify:
- Decision CRUD operations with amount/cadence/status
- Unique constraint enforcement (one decision per journal_contact)
- Ownership validation (cannot access other users' decisions)
- Filtering by journal_contact_id and journal_id
- History tracking on updates
- Monthly equivalent calculation for all cadences
- Paginated history retrieval
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.contacts.models import Contact
from apps.journals.models import Decision, DecisionHistory, Journal, JournalContact

User = get_user_model()


class DecisionAPITests(APITestCase):
    """Test suite for decision CRUD API endpoints."""

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

    # Success Criterion 1: Record decision with amount/cadence/status

    def test_create_decision_success(self):
        """Test successfully creating a decision with all fields."""
        url = reverse('journals:decision-list')
        data = {
            'journal_contact': str(self.jc1.id),
            'amount': '100.00',
            'cadence': 'monthly',
            'status': 'pending'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(str(response.data['journal_contact']), str(self.jc1.id))
        self.assertEqual(str(response.data['amount']), '100.00')
        self.assertEqual(response.data['cadence'], 'monthly')
        self.assertEqual(response.data['status'], 'pending')
        self.assertIn('monthly_equivalent', response.data)
        self.assertEqual(Decision.objects.count(), 1)

    def test_create_decision_all_cadences(self):
        """Test creating decisions with each cadence value."""
        url = reverse('journals:decision-list')

        # Create separate journal contacts for each test
        contacts = []
        for i in range(4):
            contact = Contact.objects.create(
                owner=self.user_a,
                first_name=f'Contact{i}',
                last_name='Test',
                email=f'contact{i}@example.com'
            )
            jc = JournalContact.objects.create(
                journal=self.journal,
                contact=contact
            )
            contacts.append(jc)

        cadences = ['one_time', 'monthly', 'quarterly', 'annual']

        for idx, cadence in enumerate(cadences):
            response = self.client.post(url, {
                'journal_contact': str(contacts[idx].id),
                'amount': '100.00',
                'cadence': cadence
            }, format='json')

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"Failed to create decision with cadence={cadence}"
            )
            self.assertEqual(response.data['cadence'], cadence)

    def test_create_decision_all_statuses(self):
        """Test creating decisions with each status value."""
        url = reverse('journals:decision-list')

        # Create separate journal contacts for each test
        contacts = []
        for i in range(4):
            contact = Contact.objects.create(
                owner=self.user_a,
                first_name=f'StatusContact{i}',
                last_name='Test',
                email=f'statuscontact{i}@example.com'
            )
            jc = JournalContact.objects.create(
                journal=self.journal,
                contact=contact
            )
            contacts.append(jc)

        statuses = ['pending', 'active', 'paused', 'declined']

        for idx, status_value in enumerate(statuses):
            response = self.client.post(url, {
                'journal_contact': str(contacts[idx].id),
                'amount': '100.00',
                'status': status_value
            }, format='json')

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"Failed to create decision with status={status_value}"
            )
            self.assertEqual(response.data['status'], status_value)

    def test_create_decision_without_optional_fields(self):
        """Test creating decision with only required fields, defaults should apply."""
        url = reverse('journals:decision-list')
        data = {
            'journal_contact': str(self.jc1.id),
            'amount': '100.00'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Defaults from model: cadence=monthly, status=pending
        self.assertEqual(response.data['cadence'], 'monthly')
        self.assertEqual(response.data['status'], 'pending')

    # Success Criterion 5: Unique constraint

    def test_duplicate_decision_returns_400(self):
        """Test that creating a second decision for same journal_contact returns 400."""
        url = reverse('journals:decision-list')
        data = {
            'journal_contact': str(self.jc1.id),
            'amount': '100.00'
        }

        # First POST should succeed
        response1 = self.client.post(url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second POST should fail with 400
        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        # Should contain error message about duplicate/already exists
        response_str = str(response2.data).lower()
        self.assertTrue('already exists' in response_str or 'duplicate' in response_str)

    def test_different_contacts_can_have_decisions(self):
        """Test that different journal_contacts in same journal can each have decisions."""
        url = reverse('journals:decision-list')

        # Create decision for jc1
        response1 = self.client.post(url, {
            'journal_contact': str(self.jc1.id),
            'amount': '100.00'
        }, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Create decision for jc2 (different contact, same journal)
        response2 = self.client.post(url, {
            'journal_contact': str(self.jc2.id),
            'amount': '200.00'
        }, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Both decisions should exist
        self.assertEqual(Decision.objects.count(), 2)

    # Ownership validation

    def test_cannot_create_decision_for_other_users_journal(self):
        """Test that user_b cannot create decision for user_a's journal_contact."""
        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:decision-list')
        data = {
            'journal_contact': str(self.jc1.id),  # Owned by user_a
            'amount': '100.00'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('journal_contact', response.data)

    def test_cannot_list_other_users_decisions(self):
        """Test that user_b cannot see user_a's decisions."""
        # Create decision for user_a's journal_contact
        Decision.objects.create(
            journal_contact=self.jc1,
            amount=Decimal('100.00')
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:decision-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # user_b should see 0 decisions (user_a's are filtered out)
        # Decision list uses default pagination
        self.assertEqual(response.data['count'], 0)

    def test_cannot_update_other_users_decision(self):
        """Test that user_b cannot update user_a's decision."""
        # Create decision for user_a's journal_contact
        decision = Decision.objects.create(
            journal_contact=self.jc1,
            amount=Decimal('100.00')
        )

        # Authenticate as user_b
        self.client.force_authenticate(user=self.user_b)

        url = reverse('journals:decision-detail', kwargs={'pk': decision.id})
        response = self.client.patch(url, {'amount': '200.00'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Filtering

    def test_list_decisions_filtered_by_journal_contact_id(self):
        """Test filtering decisions by journal_contact_id."""
        # Create decisions for both journal_contacts
        Decision.objects.create(journal_contact=self.jc1, amount=Decimal('100.00'))
        Decision.objects.create(journal_contact=self.jc2, amount=Decimal('200.00'))

        url = reverse('journals:decision-list')
        response = self.client.get(url, {'journal_contact_id': str(self.jc1.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(str(response.data['results'][0]['journal_contact']), str(self.jc1.id))

    def test_list_decisions_filtered_by_journal_id(self):
        """Test filtering decisions by journal_id."""
        # Create decisions for user_a's journal
        Decision.objects.create(journal_contact=self.jc1, amount=Decimal('100.00'))
        Decision.objects.create(journal_contact=self.jc2, amount=Decimal('200.00'))

        url = reverse('journals:decision-list')
        response = self.client.get(url, {'journal_id': str(self.journal.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)


class DecisionHistoryTests(APITestCase):
    """Test suite for decision history tracking, monthly equivalent, and pagination."""

    def setUp(self):
        """Set up test data with a decision ready for updates."""
        # Create user
        self.user_a = User.objects.create_user(
            email='usera@example.com',
            password='password123',
            first_name='User',
            last_name='A',
            role='staff'
        )

        # Create journal owned by user_a
        self.journal = Journal.objects.create(
            owner=self.user_a,
            name='Q1 2025 Campaign',
            goal_amount=50000.00
        )

        # Create contact and journal_contact
        self.contact = Contact.objects.create(
            owner=self.user_a,
            first_name='Alice',
            last_name='Anderson',
            email='alice@example.com',
            status='prospect'
        )
        self.jc = JournalContact.objects.create(
            journal=self.journal,
            contact=self.contact
        )

        # Create initial decision
        self.decision = Decision.objects.create(
            journal_contact=self.jc,
            amount=Decimal('100.00'),
            cadence='monthly',
            status='pending'
        )

        # Default authentication
        self.client.force_authenticate(user=self.user_a)

    # Success Criterion 2: Update appends to history

    def test_update_decision_creates_history(self):
        """Test that updating a decision creates a history record."""
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})

        response = self.client.patch(url, {'amount': '200.00'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DecisionHistory.objects.count(), 1)

        history = DecisionHistory.objects.first()
        self.assertEqual(history.decision, self.decision)
        self.assertIn('amount', history.changed_fields)
        self.assertEqual(history.changed_fields['amount'], '100.00')  # Old value
        self.assertEqual(history.changed_by, self.user_a)

    def test_update_multiple_fields_creates_single_history(self):
        """Test that updating multiple fields creates one history record with all changes."""
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})

        response = self.client.patch(url, {
            'amount': '200.00',
            'cadence': 'quarterly'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DecisionHistory.objects.count(), 1)

        history = DecisionHistory.objects.first()
        self.assertIn('amount', history.changed_fields)
        self.assertIn('cadence', history.changed_fields)
        self.assertEqual(history.changed_fields['amount'], '100.00')
        self.assertEqual(history.changed_fields['cadence'], 'monthly')

    def test_update_same_value_no_history(self):
        """Test that updating with same value creates no history record."""
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})

        # PATCH with same amount (use Decimal for exact comparison)
        response = self.client.patch(url, {'amount': Decimal('100.00')}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DecisionHistory.objects.count(), 0)

    def test_multiple_updates_create_multiple_history(self):
        """Test that sequential updates create multiple history records."""
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})

        # First update: change amount
        self.client.patch(url, {'amount': '200.00'}, format='json')

        # Second update: change cadence
        self.client.patch(url, {'cadence': 'quarterly'}, format='json')

        self.assertEqual(DecisionHistory.objects.count(), 2)

        # Should be ordered by -created_at (most recent first)
        histories = DecisionHistory.objects.all()
        self.assertIn('cadence', histories[0].changed_fields)  # Most recent
        self.assertIn('amount', histories[1].changed_fields)   # Older

    def test_history_records_old_value_not_new(self):
        """Test that history records old value, not new value."""
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})

        # Update from 100 to 200
        self.client.patch(url, {'amount': '200.00'}, format='json')

        history = DecisionHistory.objects.first()
        self.assertEqual(history.changed_fields['amount'], '100.00')  # Old value

        # Verify decision has new value
        self.decision.refresh_from_db()
        self.assertEqual(str(self.decision.amount), '200.00')

    # Success Criterion 3: Monthly equivalent calculation

    def test_monthly_equivalent_monthly(self):
        """Test monthly equivalent for monthly cadence."""
        # Create new jc for this test (self.jc already has a decision from setUp)
        contact1 = Contact.objects.create(
            owner=self.user_a,
            first_name='Test',
            last_name='Monthly',
            email='monthly@example.com'
        )
        jc1 = JournalContact.objects.create(journal=self.journal, contact=contact1)

        url = reverse('journals:decision-list')
        response = self.client.post(url, {
            'journal_contact': str(jc1.id),
            'amount': '100.00',
            'cadence': 'monthly'
        }, format='json')

        self.assertEqual(str(response.data['monthly_equivalent']), '100.00')

    def test_monthly_equivalent_quarterly(self):
        """Test monthly equivalent for quarterly cadence."""
        # Create new jc for this test
        contact2 = Contact.objects.create(
            owner=self.user_a,
            first_name='Bob',
            last_name='Brown',
            email='bob@example.com'
        )
        jc2 = JournalContact.objects.create(journal=self.journal, contact=contact2)

        url = reverse('journals:decision-list')
        response = self.client.post(url, {
            'journal_contact': str(jc2.id),
            'amount': '300.00',
            'cadence': 'quarterly'
        }, format='json')

        self.assertEqual(str(response.data['monthly_equivalent']), '100.00')

    def test_monthly_equivalent_annual(self):
        """Test monthly equivalent for annual cadence."""
        # Create new jc for this test
        contact3 = Contact.objects.create(
            owner=self.user_a,
            first_name='Charlie',
            last_name='Clark',
            email='charlie@example.com'
        )
        jc3 = JournalContact.objects.create(journal=self.journal, contact=contact3)

        url = reverse('journals:decision-list')
        response = self.client.post(url, {
            'journal_contact': str(jc3.id),
            'amount': '1200.00',
            'cadence': 'annual'
        }, format='json')

        self.assertEqual(str(response.data['monthly_equivalent']), '100.00')

    def test_monthly_equivalent_one_time(self):
        """Test monthly equivalent for one_time cadence is 0."""
        # Create new jc for this test
        contact4 = Contact.objects.create(
            owner=self.user_a,
            first_name='Diana',
            last_name='Davis',
            email='diana@example.com'
        )
        jc4 = JournalContact.objects.create(journal=self.journal, contact=contact4)

        url = reverse('journals:decision-list')
        response = self.client.post(url, {
            'journal_contact': str(jc4.id),
            'amount': '500.00',
            'cadence': 'one_time'
        }, format='json')

        self.assertEqual(str(response.data['monthly_equivalent']), '0.00')

    def test_monthly_equivalent_updates_after_cadence_change(self):
        """Test that monthly_equivalent recalculates when cadence changes."""
        # Create decision with monthly cadence
        contact5 = Contact.objects.create(
            owner=self.user_a,
            first_name='Eve',
            last_name='Evans',
            email='eve@example.com'
        )
        jc5 = JournalContact.objects.create(journal=self.journal, contact=contact5)
        decision = Decision.objects.create(
            journal_contact=jc5,
            amount=Decimal('100.00'),
            cadence='monthly'
        )

        # PATCH to quarterly
        url = reverse('journals:decision-detail', kwargs={'pk': decision.id})
        response = self.client.patch(url, {'cadence': 'quarterly'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['monthly_equivalent']), '33.33')

    # Success Criterion 4: Paginated history

    def test_history_list_paginated_default_25(self):
        """Test that history list defaults to 25 records per page."""
        # Create 30 history records by updating decision 30 times
        # Start from 101 to ensure each update is different from initial 100
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})
        for i in range(1, 31):  # 1 to 30 (30 updates)
            self.client.patch(url, {'amount': str(Decimal('100.00') + i)}, format='json')

        # GET history
        history_url = reverse('journals:decision-history-list')
        response = self.client.get(history_url, {'decision_id': str(self.decision.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 30)  # Total count
        self.assertEqual(len(response.data['results']), 25)  # Page 1 size
        self.assertIsNotNone(response.data['next'])  # Has next page

    def test_history_list_page_2(self):
        """Test getting page 2 of history."""
        # Create 30 history records
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})
        for i in range(1, 31):  # 1 to 30 (30 updates)
            self.client.patch(url, {'amount': str(Decimal('100.00') + i)}, format='json')

        # GET page 2
        history_url = reverse('journals:decision-history-list')
        response = self.client.get(history_url, {
            'decision_id': str(self.decision.id),
            'page': 2
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)  # Remaining records
        self.assertIsNone(response.data['next'])  # No more pages

    def test_history_list_custom_page_size(self):
        """Test custom page_size parameter."""
        # Create 10 history records
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})
        for i in range(10):
            self.client.patch(url, {'amount': str(100 + i)}, format='json')

        # GET with page_size=5
        history_url = reverse('journals:decision-history-list')
        response = self.client.get(history_url, {
            'decision_id': str(self.decision.id),
            'page_size': 5
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_history_filtered_by_journal_contact_id(self):
        """Test filtering history by journal_contact_id."""
        # Create second journal_contact with decision
        contact2 = Contact.objects.create(
            owner=self.user_a,
            first_name='Bob',
            last_name='Brown',
            email='bob2@example.com'
        )
        jc2 = JournalContact.objects.create(journal=self.journal, contact=contact2)
        decision2 = Decision.objects.create(
            journal_contact=jc2,
            amount=Decimal('200.00')
        )

        # Create history for both decisions
        url1 = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})
        self.client.patch(url1, {'amount': '150.00'}, format='json')

        url2 = reverse('journals:decision-detail', kwargs={'pk': decision2.id})
        self.client.patch(url2, {'amount': '250.00'}, format='json')

        # GET history filtered by jc
        history_url = reverse('journals:decision-history-list')
        response = self.client.get(history_url, {
            'journal_contact_id': str(self.jc.id)
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        # Verify it's the right decision's history
        self.assertEqual(
            str(response.data['results'][0]['decision']),
            str(self.decision.id)
        )

    # Atomic transaction integrity

    def test_history_and_update_are_atomic(self):
        """Test that decision update and history creation are atomic."""
        url = reverse('journals:decision-detail', kwargs={'pk': self.decision.id})

        response = self.client.patch(url, {'amount': '200.00'}, format='json')

        # Both should succeed together
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Decision updated
        self.decision.refresh_from_db()
        self.assertEqual(str(self.decision.amount), '200.00')

        # History created
        self.assertEqual(DecisionHistory.objects.count(), 1)
