"""Regression tests for the report_3 #1 sibling leak via the events API.

Finding #1 was fixed only in the dashboard "what changed" feed. The standalone
events API (GET /api/v1/events/ and /<id>/) reads the same Event rows through
get_visible_user_ids — which includes coached users for a coach — and applied
no financial gating, so a coach could still read a coached user's journal goal
("Goal: $X") and donation amounts ("$X received") (CWE-200).

These tests pin the gate closed via the shared policy in apps/events/policy.py:

  - a coach's events list omits dollar-bearing events (journal goal + donation);
  - a coach fetching a financial event by id gets 404;
  - a coach STILL sees non-financial events (no over-gating);
  - a missionary (financial role) still sees everything (no over-gating).

Each test fails if the gate is reverted (project rule #1).
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.events.models import Event, EventSeverity, EventType
from apps.gifts.models import Gift
from apps.journals.models import Journal

User = get_user_model()

GOAL = "9000.99"  # distinctive journal goal — must be absent from coach responses
GIFT_CENTS = 777777  # $7,777.77 — distinctive donation amount → "$7777.77 received"


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def events_setup(db):
    """Coach C coaches missionary M. M has a journal-goal event, a donation
    event, and one non-financial event the coach is allowed to see."""
    missionary = User.objects.create_user(
        email="m-evt@example.com", password="pw", first_name="Mae", last_name="M", role="missionary"
    )
    coach = User.objects.create_user(
        email="c-evt@example.com", password="pw", first_name="Cal", last_name="C", role="coach"
    )
    coach.coached_users.add(missionary)

    # Fires JOURNAL_CREATED → message "Goal: $9000.99" + metadata.goal_amount.
    Journal.objects.create(owner=missionary, name="2026 MPD", goal_amount=GOAL)

    # Fires DONATION_RECEIVED → message "$7777.77 received".
    contact = Contact.objects.create(
        owner=missionary, first_name="Dee", last_name="Donor", status="donor"
    )
    Gift.objects.create(donor_contact=contact, amount_cents=GIFT_CENTS, gift_date=date.today())

    # Non-financial event the coach legitimately sees (no over-gating control).
    non_financial = Event.objects.create(
        user=missionary,
        event_type=EventType.CONTACT_CREATED,
        title="Contact created",
        message="No money here.",
        severity=EventSeverity.INFO,
    )
    return {"missionary": missionary, "coach": coach, "non_financial": non_financial}


@pytest.mark.django_db
class TestCoachEventsApiFinancialLeak:
    def test_coach_list_omits_financial_events(self, events_setup):
        resp = _client(events_setup["coach"]).get("/api/v1/events/")
        assert resp.status_code == status.HTTP_200_OK
        body = str(resp.data)
        assert GOAL not in body
        assert "7777.77" not in body
        results = resp.data["results"] if "results" in resp.data else resp.data
        types = {e["event_type"] for e in results}
        assert "journal_created" not in types
        assert "donation_received" not in types
        # No over-gating: the non-financial event is still delivered.
        assert "contact_created" in types

    def test_coach_detail_404s_on_financial_event(self, events_setup):
        journal_event = Event.objects.get(
            user=events_setup["missionary"], event_type=EventType.JOURNAL_CREATED
        )
        resp = _client(events_setup["coach"]).get(f"/api/v1/events/{journal_event.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_coach_detail_allows_non_financial_event(self, events_setup):
        resp = _client(events_setup["coach"]).get(
            f"/api/v1/events/{events_setup['non_financial'].id}/"
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_missionary_list_includes_financial_events(self, events_setup):
        """Financial role still sees the amounts (no over-gating)."""
        resp = _client(events_setup["missionary"]).get("/api/v1/events/")
        assert resp.status_code == status.HTTP_200_OK
        body = str(resp.data)
        assert GOAL in body
        assert "7777.77" in body
