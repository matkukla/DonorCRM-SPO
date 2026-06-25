"""
Tests for Gift signal handlers.

Verifies that:
- Creating a Gift triggers contact stat update (total_given, gift_count)
- Creating a Gift sets needs_thank_you=True on the contact
- Creating a Gift creates a DONATION_RECEIVED event
- Updating a Gift amount triggers contact stat recalculation
- Deleting a Gift triggers contact stat recalculation
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.contacts.models import ContactStatus
from apps.contacts.tests.factories import ContactFactory
from apps.events.models import Event, EventType
from apps.gifts.models import Gift, RecurringGift, RecurringGiftFrequency, RecurringGiftStatus
from apps.users.tests.factories import UserFactory


@pytest.fixture
def staff_user():
    return UserFactory(email="signal-test@test.com")


@pytest.fixture
def contact(staff_user):
    return ContactFactory(
        owner=staff_user,
        first_name="Signal",
        last_name="Test",
        status=ContactStatus.PROSPECT,
        needs_thank_you=False,
    )


@pytest.mark.django_db
class TestGiftSignalCreate:
    """Test signals fired on Gift creation."""

    def test_create_gift_updates_contact_total_given(self, contact):
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
        )
        contact.refresh_from_db()
        assert contact.total_given == Decimal("100.00")
        assert contact.gift_count == 1

    def test_create_gift_sets_needs_thank_you(self, contact):
        assert contact.needs_thank_you is False
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=5000,
            gift_date=date.today(),
        )
        contact.refresh_from_db()
        assert contact.needs_thank_you is True

    def test_create_gift_creates_event(self, contact):
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
        )
        event = Event.objects.filter(
            contact=contact,
            event_type=EventType.DONATION_RECEIVED,
        ).first()
        assert event is not None
        assert "$100" in event.message

    def test_create_gift_updates_first_and_last_gift_date(self, contact):
        gift_date = date(2025, 6, 15)
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=gift_date,
        )
        contact.refresh_from_db()
        assert contact.first_gift_date == gift_date
        assert contact.last_gift_date == gift_date

    def test_create_gift_promotes_prospect_to_donor(self, contact):
        assert contact.status == ContactStatus.PROSPECT
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
        )
        contact.refresh_from_db()
        assert contact.status == ContactStatus.DONOR

    def test_multiple_gifts_accumulate_stats(self, contact):
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today() - timedelta(days=10),
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=5000,
            gift_date=date.today(),
        )
        contact.refresh_from_db()
        assert contact.total_given == Decimal("150.00")
        assert contact.gift_count == 2


@pytest.mark.django_db
class TestGiftSignalUpdate:
    """Test signals fired on Gift update."""

    def test_update_gift_amount_recalculates_stats(self, contact):
        gift = Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
        )
        contact.refresh_from_db()
        assert contact.total_given == Decimal("100.00")

        gift.amount_cents = 20000
        gift.save()

        contact.refresh_from_db()
        assert contact.total_given == Decimal("200.00")

    def test_update_gift_date_recalculates_dates(self, contact):
        gift = Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date(2025, 1, 1),
        )
        contact.refresh_from_db()
        assert contact.last_gift_date == date(2025, 1, 1)

        gift.gift_date = date(2025, 6, 15)
        gift.save()

        contact.refresh_from_db()
        assert contact.last_gift_date == date(2025, 6, 15)


@pytest.mark.django_db
class TestGiftSignalDelete:
    """Test signals fired on Gift deletion."""

    def test_delete_gift_recalculates_stats(self, contact):
        gift1 = Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today() - timedelta(days=10),
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=5000,
            gift_date=date.today(),
        )
        contact.refresh_from_db()
        assert contact.total_given == Decimal("150.00")
        assert contact.gift_count == 2

        gift1.delete()

        contact.refresh_from_db()
        assert contact.total_given == Decimal("50.00")
        assert contact.gift_count == 1

    def test_delete_all_gifts_resets_stats(self, contact):
        gift = Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
        )
        contact.refresh_from_db()
        assert contact.gift_count == 1

        gift.delete()

        contact.refresh_from_db()
        assert contact.total_given == Decimal("0.00")
        assert contact.gift_count == 0


@pytest.mark.django_db
class TestRecurringGiftSignals:
    """Test that recurring-sourced gifts skip notifications and RecurringGift signals work."""

    def test_recurring_gift_does_not_set_needs_thank_you(self, contact):
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date.today(),
            status=RecurringGiftStatus.ACTIVE,
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
            recurring_gift=rg,
        )
        contact.refresh_from_db()
        assert contact.needs_thank_you is False

    def test_recurring_gift_does_not_create_event(self, contact):
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date.today(),
            status=RecurringGiftStatus.ACTIVE,
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
            recurring_gift=rg,
        )
        events = Event.objects.filter(
            contact=contact,
            event_type=EventType.DONATION_RECEIVED,
        )
        assert events.count() == 0

    def test_recurring_gift_still_updates_stats(self, contact):
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date.today(),
            status=RecurringGiftStatus.ACTIVE,
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
            recurring_gift=rg,
        )
        contact.refresh_from_db()
        assert contact.total_given == Decimal("100.00")
        assert contact.gift_count == 1

    def test_recurring_gift_delete_removes_linked_gifts(self, contact):
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date.today(),
            status=RecurringGiftStatus.ACTIVE,
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today(),
            recurring_gift=rg,
        )
        Gift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=date.today() - timedelta(days=30),
            recurring_gift=rg,
        )
        assert Gift.objects.filter(recurring_gift=rg).count() == 2
        rg.delete()
        assert Gift.objects.filter(donor_contact=contact).count() == 0
        contact.refresh_from_db()
        assert contact.total_given == Decimal("0.00")


@pytest.mark.django_db
class TestEnqueueThankYouForRecentImports:
    """F4 / ADR 0006: the import-path thank-you helper.

    Importers disable gift signals, so the UI signal's "fresh gift enqueues a
    thank-you" rule never fires on import. This helper restores that intent
    only for recent, non-recurring gifts.
    """

    def _make_contact(self):
        return ContactFactory(owner=UserFactory(), needs_thank_you=False)

    def test_recent_non_recurring_gift_is_flagged(self):
        from apps.gifts.signals import (
            disable_gift_signals,
            enable_gift_signals,
            enqueue_thank_you_for_recent_imports,
        )

        contact = self._make_contact()
        disable_gift_signals()
        try:
            Gift.objects.create(
                donor_contact=contact,
                amount_cents=10000,
                gift_date=date.today() - timedelta(days=3),
            )
        finally:
            enable_gift_signals()

        enqueue_thank_you_for_recent_imports([contact.id])
        contact.refresh_from_db()
        assert contact.needs_thank_you is True

    def test_old_gift_is_not_flagged(self):
        from apps.gifts.signals import (
            disable_gift_signals,
            enable_gift_signals,
            enqueue_thank_you_for_recent_imports,
        )

        contact = self._make_contact()
        disable_gift_signals()
        try:
            Gift.objects.create(
                donor_contact=contact,
                amount_cents=10000,
                gift_date=date.today() - timedelta(days=120),
            )
        finally:
            enable_gift_signals()

        enqueue_thank_you_for_recent_imports([contact.id])
        contact.refresh_from_db()
        assert contact.needs_thank_you is False

    def test_recurring_sourced_gift_is_not_flagged(self):
        from apps.gifts.signals import (
            disable_gift_signals,
            enable_gift_signals,
            enqueue_thank_you_for_recent_imports,
        )

        contact = self._make_contact()
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            status=RecurringGiftStatus.ACTIVE,
            start_date=date.today() - timedelta(days=90),
        )
        disable_gift_signals()
        try:
            Gift.objects.create(
                donor_contact=contact,
                amount_cents=10000,
                gift_date=date.today() - timedelta(days=3),
                recurring_gift=rg,
            )
        finally:
            enable_gift_signals()

        enqueue_thank_you_for_recent_imports([contact.id])
        contact.refresh_from_db()
        assert contact.needs_thank_you is False
