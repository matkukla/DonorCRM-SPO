"""Regression tests for the 2026-06-22 report_3 re-scan findings #1 and #5.

A coach (non-financial role) viewing a coached missionary's dashboard must not
receive any dollar figure (CWE-200):

  #1 — the what-changed event feed must not surface the JOURNAL_CREATED event,
       whose message/metadata carry "Goal: $<goal_amount>".
  #5 — the dashboard summary must not return late_donations rows, which carry
       per-pledge amount and monthly_equivalent.

A missionary (financial role) still sees both, proving no over-gating. Each
test fails if a gate is reverted (project rule #1): the distinctive amounts
must never appear in a coach response body.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import RecurringGift
from apps.journals.models import Journal

User = get_user_model()

GOAL = "9000.99"  # distinctive journal goal — must be absent from coach responses
PLEDGE_CENTS = 777777  # $7,777.77 — distinctive late-pledge amount


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def coached_pair(db):
    """Coach C coaches missionary M."""
    missionary = User.objects.create_user(
        email="m-r3@example.com",
        password="pw",
        first_name="Mara",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-r3@example.com",
        password="pw",
        first_name="Cole",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    return {"missionary": missionary, "coach": coach}


@pytest.mark.django_db
class TestCoachDashboardEventGoalLeak:
    """Finding #1 — JOURNAL_CREATED 'Goal: $X' must not reach a coach's feed."""

    def test_coach_event_feed_omits_journal_goal(self, coached_pair):
        # Creating the journal fires the JOURNAL_CREATED event (is_new=True).
        Journal.objects.create(owner=coached_pair["missionary"], name="2026 MPD", goal_amount=GOAL)
        resp = _client(coached_pair["coach"]).get(
            f"/api/v1/dashboard/?user_id={coached_pair['missionary'].id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert GOAL not in str(resp.data)
        event_types = {e.get("event_type") for e in resp.data["what_changed"]["recent_events"]}
        assert "journal_created" not in event_types

    def test_missionary_event_feed_includes_journal_goal(self, coached_pair):
        """Financial role still sees the journal-created event (no over-gating)."""
        Journal.objects.create(owner=coached_pair["missionary"], name="2026 MPD", goal_amount=GOAL)
        resp = _client(coached_pair["missionary"]).get("/api/v1/dashboard/")
        assert resp.status_code == status.HTTP_200_OK
        assert GOAL in str(resp.data)


@pytest.mark.django_db
class TestCoachDashboardLateDonationLeak:
    """Finding #5 — dashboard summary late_donations withheld from a coach."""

    @pytest.fixture
    def with_late_pledge(self, coached_pair):
        contact = Contact.objects.create(
            owner=coached_pair["missionary"],
            first_name="Dana",
            last_name="Donor",
            status="donor",
        )
        RecurringGift.objects.create(
            donor_contact=contact,
            amount_cents=PLEDGE_CENTS,
            frequency="monthly",
            start_date=date.today() - timedelta(days=120),
            status="active",
        )
        return coached_pair

    def test_coach_summary_omits_late_donations(self, with_late_pledge):
        resp = _client(with_late_pledge["coach"]).get(
            f"/api/v1/dashboard/?user_id={with_late_pledge['missionary'].id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["late_donations"] == []
        assert resp.data["late_donations_count"] == 0
        # The amount must be absent from the late-donations surface (finding #5).
        # It may still appear in the support_progress aggregate tile, which
        # coaches are intentionally permitted to see (report_3 Open Question #1 /
        # pilot-audit decision). The N=1 aggregate-inference edge is a known,
        # accepted residual risk and is out of scope for #5.
        assert "7777" not in str(resp.data["late_donations"])

    def test_missionary_summary_includes_late_donations(self, with_late_pledge):
        """Financial role still sees the late pledge with its amount."""
        resp = _client(with_late_pledge["missionary"]).get("/api/v1/dashboard/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["late_donations_count"] == 1
        assert "7777" in str(resp.data)
