"""
Tests for recurring gift payment generation utilities.
"""

from datetime import date

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.models import Gift, RecurringGift, RecurringGiftFrequency, RecurringGiftStatus
from apps.gifts.recurring_utils import (
    generate_gifts_for_recurring,
    generate_payment_dates,
    make_recurring_external_id,
    sync_recurring_gift_payments,
)
from apps.users.tests.factories import UserFactory


class TestGeneratePaymentDates:
    """Test payment date generation for various frequencies."""

    def test_monthly_generates_correct_dates(self):
        dates = generate_payment_dates(
            start_date=date(2026, 1, 1),
            end_date=None,
            frequency=RecurringGiftFrequency.MONTHLY,
            cutoff_date=date(2026, 4, 1),
        )
        assert dates == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]

    def test_quarterly_generates_correct_dates(self):
        dates = generate_payment_dates(
            start_date=date(2026, 1, 1),
            end_date=None,
            frequency=RecurringGiftFrequency.QUARTERLY,
            cutoff_date=date(2026, 7, 1),
        )
        assert dates == [date(2026, 1, 1), date(2026, 4, 1), date(2026, 7, 1)]

    def test_annually_generates_correct_dates(self):
        dates = generate_payment_dates(
            start_date=date(2024, 6, 15),
            end_date=None,
            frequency=RecurringGiftFrequency.ANNUALLY,
            cutoff_date=date(2026, 7, 1),
        )
        assert dates == [date(2024, 6, 15), date(2025, 6, 15), date(2026, 6, 15)]

    def test_weekly_generates_correct_dates(self):
        dates = generate_payment_dates(
            start_date=date(2026, 3, 1),
            end_date=None,
            frequency=RecurringGiftFrequency.WEEKLY,
            cutoff_date=date(2026, 3, 22),
        )
        assert len(dates) == 4  # Mar 1, 8, 15, 22

    def test_biweekly_generates_correct_dates(self):
        dates = generate_payment_dates(
            start_date=date(2026, 3, 1),
            end_date=None,
            frequency=RecurringGiftFrequency.BIWEEKLY,
            cutoff_date=date(2026, 3, 29),
        )
        assert dates == [date(2026, 3, 1), date(2026, 3, 15), date(2026, 3, 29)]

    def test_end_date_caps_generation(self):
        dates = generate_payment_dates(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 1),
            frequency=RecurringGiftFrequency.MONTHLY,
            cutoff_date=date(2026, 12, 31),
        )
        assert dates == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]

    def test_irregular_returns_empty(self):
        dates = generate_payment_dates(
            start_date=date(2026, 1, 1),
            end_date=None,
            frequency=RecurringGiftFrequency.IRREGULAR,
            cutoff_date=date(2026, 12, 31),
        )
        assert dates == []

    def test_future_start_returns_empty(self):
        dates = generate_payment_dates(
            start_date=date(2099, 1, 1),
            end_date=None,
            frequency=RecurringGiftFrequency.MONTHLY,
            cutoff_date=date(2026, 4, 1),
        )
        assert dates == []

    def test_start_equals_cutoff_returns_one(self):
        dates = generate_payment_dates(
            start_date=date(2026, 4, 1),
            end_date=None,
            frequency=RecurringGiftFrequency.MONTHLY,
            cutoff_date=date(2026, 4, 1),
        )
        assert dates == [date(2026, 4, 1)]


class TestMakeRecurringExternalId:
    """Test external ID generation for recurring payments."""

    def test_monthly_uses_year_month(self):
        ext_id = make_recurring_external_id(
            "12345",
            date(2026, 3, 1),
            RecurringGiftFrequency.MONTHLY,
        )
        assert ext_id == "rg_12345_2026-03"

    def test_weekly_uses_full_date(self):
        ext_id = make_recurring_external_id(
            "12345",
            date(2026, 3, 8),
            RecurringGiftFrequency.WEEKLY,
        )
        assert ext_id == "rg_12345_2026-03-08"

    def test_biweekly_uses_full_date(self):
        ext_id = make_recurring_external_id(
            "12345",
            date(2026, 3, 15),
            RecurringGiftFrequency.BIWEEKLY,
        )
        assert ext_id == "rg_12345_2026-03-15"

    def test_quarterly_uses_year_month(self):
        ext_id = make_recurring_external_id(
            "99",
            date(2026, 4, 1),
            RecurringGiftFrequency.QUARTERLY,
        )
        assert ext_id == "rg_99_2026-04"


@pytest.mark.django_db
class TestGenerateGiftsForRecurring:
    """Test Gift record generation from RecurringGift."""

    def test_creates_gift_records(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
            external_gift_id="test_rg_001",
        )
        count = generate_gifts_for_recurring(rg, cutoff_date=date(2026, 3, 1))
        assert count == 3
        assert Gift.objects.filter(recurring_gift=rg).count() == 3

    def test_idempotent_on_second_call(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
            external_gift_id="test_rg_002",
        )
        generate_gifts_for_recurring(rg, cutoff_date=date(2026, 3, 1))
        count2 = generate_gifts_for_recurring(rg, cutoff_date=date(2026, 3, 1))
        assert count2 == 0
        assert Gift.objects.filter(recurring_gift=rg).count() == 3

    def test_irregular_creates_nothing(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.IRREGULAR,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
        )
        count = generate_gifts_for_recurring(rg, cutoff_date=date(2026, 3, 1))
        assert count == 0

    def test_uses_uuid_when_no_external_id(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=5000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
        )
        count = generate_gifts_for_recurring(rg, cutoff_date=date(2026, 2, 1))
        assert count == 2
        gift = Gift.objects.filter(recurring_gift=rg).first()
        assert str(rg.pk) in gift.external_gift_id

    def test_gift_has_correct_fields(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
            external_gift_id="test_rg_fields",
        )
        generate_gifts_for_recurring(rg, cutoff_date=date(2026, 1, 1))
        gift = Gift.objects.filter(recurring_gift=rg).first()
        assert gift.donor_contact == contact
        assert gift.amount_cents == 10000
        assert gift.gift_date == date(2026, 1, 1)
        assert gift.recurring_gift == rg
        assert "Recurring payment" in gift.description


@pytest.mark.django_db
class TestSyncRecurringGiftPayments:
    """Test sync logic when a RecurringGift is updated."""

    def test_sync_creates_missing_gifts(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
            external_gift_id="sync_001",
        )
        sync_recurring_gift_payments(rg, cutoff_date=date(2026, 3, 1))
        assert Gift.objects.filter(recurring_gift=rg).count() == 3

    def test_sync_updates_amount(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
            external_gift_id="sync_002",
        )
        sync_recurring_gift_payments(rg, cutoff_date=date(2026, 2, 1))
        # Change amount
        rg.amount_cents = 20000
        rg.save(update_fields=["amount_cents"])
        sync_recurring_gift_payments(rg, cutoff_date=date(2026, 2, 1))
        for gift in Gift.objects.filter(recurring_gift=rg):
            assert gift.amount_cents == 20000

    def test_sync_deletes_gifts_beyond_end_date(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
            external_gift_id="sync_003",
        )
        sync_recurring_gift_payments(rg, cutoff_date=date(2026, 4, 1))
        assert Gift.objects.filter(recurring_gift=rg).count() == 4
        # Shorten end date
        rg.end_date = date(2026, 2, 1)
        rg.save(update_fields=["end_date"])
        sync_recurring_gift_payments(rg, cutoff_date=date(2026, 4, 1))
        assert Gift.objects.filter(recurring_gift=rg).count() == 2

    def test_sync_cancelled_deletes_all(self):
        user = UserFactory()
        contact = ContactFactory(owner=user)
        rg = RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=10000,
            frequency=RecurringGiftFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            status=RecurringGiftStatus.ACTIVE,
            external_gift_id="sync_004",
        )
        sync_recurring_gift_payments(rg, cutoff_date=date(2026, 3, 1))
        assert Gift.objects.filter(recurring_gift=rg).count() == 3
        rg.status = RecurringGiftStatus.CANCELLED
        rg.save(update_fields=["status"])
        sync_recurring_gift_payments(rg, cutoff_date=date(2026, 3, 1))
        assert Gift.objects.filter(recurring_gift=rg).count() == 0
