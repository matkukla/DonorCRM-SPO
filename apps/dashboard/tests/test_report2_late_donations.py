"""Regression test for the 2026-06-22 re-scan finding #5.

The dashboard late-donations endpoint returns per-pledge amount and
monthly_equivalent. A coach (non-financial role) must not receive that
individual financial detail (CWE-200), matching the gate already on
RecentGiftsView. A missionary (financial role) still sees the rows.

Each test fails if the gate is reverted (project rule #1). The distinctive
amount 7777.77 must never appear in a coach response body.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import RecurringGift

User = get_user_model()

PLEDGE_CENTS = 777777  # $7,777.77 — distinctive, must be absent from coach responses


@pytest.fixture
def late_setup(db):
    """Coach C coaches missionary M, who has one overdue monthly pledge."""
    missionary = User.objects.create_user(
        email="m-late@example.com",
        password="pw",
        first_name="Mara",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-late@example.com",
        password="pw",
        first_name="Cole",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    contact = Contact.objects.create(
        owner=missionary, first_name="Dana", last_name="Donor", status="donor"
    )
    # Monthly pledge whose reference date (start_date, no gift yet) is well past
    # the 45-day grace window -> "late".
    RecurringGift.objects.create(
        donor_contact=contact,
        amount_cents=PLEDGE_CENTS,
        frequency="monthly",
        start_date=date.today() - timedelta(days=120),
        status="active",
    )
    return {"missionary": missionary, "coach": coach}


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestCoachLateDonations:
    def test_coach_late_donations_empty(self, late_setup):
        resp = _client(late_setup["coach"]).get(
            f"/api/v1/dashboard/late-donations/?user_id={late_setup['missionary'].id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["late_donations"] == []
        assert resp.data["total_count"] == 0
        assert "7777" not in str(resp.data)

    def test_missionary_late_donations_present(self, late_setup):
        """Financial role still sees the late pledge with its amount (no over-gating)."""
        resp = _client(late_setup["missionary"]).get("/api/v1/dashboard/late-donations/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_count"] == 1
        assert "7777" in str(resp.data)
