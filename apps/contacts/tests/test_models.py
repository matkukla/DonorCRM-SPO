"""
Tests for Contact model methods.
"""
from decimal import Decimal

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestUpdateGivingStats:
    """Tests for Contact.update_giving_stats()."""

    def test_last_gift_amount_cleared_when_all_gifts_deleted(self):
        """Deleting all gifts should clear last_gift_amount to None."""
        user = UserFactory(role='missionary')
        contact = ContactFactory(owner=user)

        # Create a gift and update stats
        gift = GiftFactory(donor_contact=contact, amount_cents=5000)
        contact.update_giving_stats()
        contact.refresh_from_db()
        assert contact.last_gift_amount == Decimal('50.00')

        # Delete the gift and update stats
        gift.delete()
        contact.update_giving_stats()
        contact.refresh_from_db()

        assert contact.last_gift_amount is None
        assert contact.gift_count == 0
        assert contact.total_given == Decimal('0')
