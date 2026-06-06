"""
Tests for the /insights/late-donations/ endpoint.

Regression: this endpoint previously returned an empty stub even when there
were active recurring pledges that had missed their expected payment window.
Now delegates to apps.core.late_donations.compute_late_donations.
"""

from datetime import date, timedelta

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import RecurringGiftFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_late_donations_returns_overdue_pledge():
    """A monthly pledge with no gifts in 60+ days must show up."""
    from rest_framework.test import APIClient

    user = UserFactory(role="missionary")
    contact = ContactFactory(
        owner=user,
        last_gift_date=date.today() - timedelta(days=60),
    )
    RecurringGiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        frequency="monthly",
        start_date=date.today() - timedelta(days=120),
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/insights/late-donations/")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert len(body["late_donations"]) == 1
    item = body["late_donations"][0]
    assert item["contact_id"] == str(contact.id)
    assert item["days_late"] > 0
    assert isinstance(item["amount"], (int, float))
    assert isinstance(item["monthly_equivalent"], (int, float))


@pytest.mark.django_db
def test_late_donations_empty_when_on_track():
    """No late pledges => empty list."""
    from rest_framework.test import APIClient

    user = UserFactory(role="missionary")
    contact = ContactFactory(
        owner=user,
        last_gift_date=date.today() - timedelta(days=10),
    )
    RecurringGiftFactory(
        donor_contact=contact,
        amount_cents=10000,
        frequency="monthly",
        start_date=date.today() - timedelta(days=120),
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/insights/late-donations/")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 0
    assert body["late_donations"] == []


@pytest.mark.django_db
def test_count_late_donations_matches_full_list():
    """count_late_donations must match len(compute_late_donations(...)) so the
    dashboard tile's count badge agrees with the displayed list."""
    from apps.core.late_donations import (
        base_recurring_for_owner,
        compute_late_donations,
        count_late_donations,
    )

    user = UserFactory(role="missionary")
    # 3 late pledges
    for _ in range(3):
        contact = ContactFactory(
            owner=user,
            last_gift_date=date.today() - timedelta(days=60),
        )
        RecurringGiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            frequency="monthly",
            start_date=date.today() - timedelta(days=120),
        )
    # 1 on-track pledge — must NOT be counted
    on_track = ContactFactory(
        owner=user,
        last_gift_date=date.today() - timedelta(days=10),
    )
    RecurringGiftFactory(
        donor_contact=on_track,
        amount_cents=10000,
        frequency="monthly",
        start_date=date.today() - timedelta(days=120),
    )

    qs = base_recurring_for_owner(user)
    full_list = compute_late_donations(qs)
    assert count_late_donations(qs) == len(full_list) == 3


@pytest.mark.django_db
def test_late_donations_no_cross_user_leakage():
    """Missionary A must not see missionary B's late pledges."""
    from rest_framework.test import APIClient

    user_a = UserFactory(role="missionary")
    user_b = UserFactory(role="missionary")

    contact_b = ContactFactory(
        owner=user_b,
        last_gift_date=date.today() - timedelta(days=60),
    )
    RecurringGiftFactory(
        donor_contact=contact_b,
        amount_cents=10000,
        frequency="monthly",
        start_date=date.today() - timedelta(days=120),
    )

    client = APIClient()
    client.force_authenticate(user=user_a)
    response = client.get("/api/v1/insights/late-donations/")

    assert response.status_code == 200
    assert response.json()["total_count"] == 0
