"""
Tests for duplicate contact detection functionality.
SQLite-compatible -- TrigramSimilarity is mocked where needed since pg_trgm
functions do not work on SQLite.
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.contacts.models import Contact, DismissedDuplicate
from apps.contacts.tests.factories import ContactFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestFindDuplicatesForContact:
    """Test find_duplicates_for_contact service function."""

    def test_find_duplicates_exact_email_match(self):
        """Exact email match returns 'high' confidence result."""
        from apps.contacts.services import find_duplicates_for_contact

        user = UserFactory()
        existing = ContactFactory(owner=user, email='john@example.com')

        results = find_duplicates_for_contact(
            contact_data={'first_name': 'Different', 'last_name': 'Name',
                          'email': 'john@example.com', 'phone': ''},
            owner_id=user.id
        )

        assert len(results) >= 1
        match = next(r for r in results if r['contact'].id == existing.id)
        assert match['confidence'] == 'high'
        assert 'email' in ' '.join(match['reasons']).lower()

    def test_find_duplicates_exact_phone_match(self):
        """Exact phone match returns 'high' confidence result."""
        from apps.contacts.services import find_duplicates_for_contact

        user = UserFactory()
        existing = ContactFactory(owner=user, phone='555-123-4567')

        results = find_duplicates_for_contact(
            contact_data={'first_name': 'Different', 'last_name': 'Name',
                          'email': '', 'phone': '555-123-4567'},
            owner_id=user.id
        )

        assert len(results) >= 1
        match = next(r for r in results if r['contact'].id == existing.id)
        assert match['confidence'] == 'high'
        assert 'phone' in ' '.join(match['reasons']).lower()

    def test_find_duplicates_owner_scoping(self):
        """Only returns contacts owned by the specified user."""
        from apps.contacts.services import find_duplicates_for_contact

        user_a = UserFactory()
        user_b = UserFactory()
        # Same email but different owners
        ContactFactory(owner=user_a, email='shared@example.com')
        ContactFactory(owner=user_b, email='shared@example.com')

        results = find_duplicates_for_contact(
            contact_data={'first_name': '', 'last_name': '',
                          'email': 'shared@example.com', 'phone': ''},
            owner_id=user_a.id
        )

        # Only user_a's contact should appear
        owner_ids = {r['contact'].owner_id for r in results}
        assert owner_ids == {user_a.id}

    def test_find_duplicates_excludes_merged(self):
        """is_merged=True contacts are excluded from results."""
        from apps.contacts.services import find_duplicates_for_contact

        user = UserFactory()
        merged = ContactFactory(owner=user, email='merged@example.com', is_merged=True)

        results = find_duplicates_for_contact(
            contact_data={'first_name': '', 'last_name': '',
                          'email': 'merged@example.com', 'phone': ''},
            owner_id=user.id
        )

        contact_ids = {r['contact'].id for r in results}
        assert merged.id not in contact_ids

    def test_find_duplicates_excludes_self(self):
        """When exclude_id is provided, that contact is excluded."""
        from apps.contacts.services import find_duplicates_for_contact

        user = UserFactory()
        contact = ContactFactory(owner=user, email='self@example.com')

        results = find_duplicates_for_contact(
            contact_data={'first_name': '', 'last_name': '',
                          'email': 'self@example.com', 'phone': ''},
            owner_id=user.id,
            exclude_id=contact.id
        )

        contact_ids = {r['contact'].id for r in results}
        assert contact.id not in contact_ids


@pytest.mark.django_db
class TestDismissedDuplicateCanonicalization:
    """Test DismissedDuplicate model canonicalization."""

    def test_dismissed_duplicate_canonicalization(self):
        """DismissedDuplicate canonicalizes pair ordering (a_id < b_id)."""
        user = UserFactory()
        c1 = ContactFactory(owner=user)
        c2 = ContactFactory(owner=user)

        # Determine which has the "larger" UUID string
        if str(c1.id) < str(c2.id):
            larger, smaller = c2, c1
        else:
            larger, smaller = c1, c2

        # Create with larger UUID as contact_a (wrong order)
        dd = DismissedDuplicate.objects.create(
            contact_a=larger, contact_b=smaller, dismissed_by=user
        )

        dd.refresh_from_db()
        # After save, contact_a should have the smaller UUID
        assert str(dd.contact_a_id) < str(dd.contact_b_id)
        assert dd.contact_a_id == smaller.id
        assert dd.contact_b_id == larger.id
