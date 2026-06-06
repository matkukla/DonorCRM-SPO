"""
Tests for /insights/monthly-commitments/ — specifically the last_fulfilled_date
field that the frontend table renders.
"""

from datetime import date, timedelta

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.insights.services import get_monthly_commitments
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_last_fulfilled_date_uses_latest_gift_for_pledge():
    """last_fulfilled_date is MAX(gift_date) for gifts linked to the pledge."""
    user = UserFactory(role="missionary")
    contact = ContactFactory(owner=user)
    pledge = RecurringGiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        frequency="monthly",
    )
    GiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        gift_date=date(2026, 1, 15),
        recurring_gift=pledge,
    )
    GiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        gift_date=date(2026, 3, 15),
        recurring_gift=pledge,
    )

    result = get_monthly_commitments(user)

    assert len(result["pledges"]) == 1
    assert result["pledges"][0]["last_fulfilled_date"] == "2026-03-15"


@pytest.mark.django_db
def test_last_fulfilled_date_null_when_never_paid():
    """A pledge with no linked gifts surfaces last_fulfilled_date = None."""
    user = UserFactory(role="missionary")
    contact = ContactFactory(owner=user)
    RecurringGiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        frequency="monthly",
        start_date=date.today() - timedelta(days=10),
    )

    result = get_monthly_commitments(user)

    assert len(result["pledges"]) == 1
    assert result["pledges"][0]["last_fulfilled_date"] is None


@pytest.mark.django_db
def test_last_fulfilled_date_ignores_unrelated_gifts():
    """A standalone gift on the same contact (not linked to the pledge) does
    NOT count as a fulfillment."""
    user = UserFactory(role="missionary")
    contact = ContactFactory(owner=user)
    pledge = RecurringGiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        frequency="monthly",
    )
    # Linked gift
    GiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        gift_date=date(2026, 1, 15),
        recurring_gift=pledge,
    )
    # Unlinked one-time gift on same contact, more recent — must NOT win
    GiftFactory(
        donor_contact=contact, amount_cents=50000, gift_date=date(2026, 4, 1), recurring_gift=None
    )

    result = get_monthly_commitments(user)

    assert result["pledges"][0]["last_fulfilled_date"] == "2026-01-15"
