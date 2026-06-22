"""Regression test for the 2026-06-22 re-scan finding #6.

The journal-report endpoint returns aggregate financial figures
(confirmed_amount, pending_amount, goal_amount). A coach (non-financial role)
may view a coached journal's report but must not receive the money figures
(CWE-200). A missionary (financial role) still sees them.

Each test fails if the gate is reverted (project rule #1). The distinctive
amounts must never appear in a coach response body.
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.journals.models import Decision, Journal, JournalContact

User = get_user_model()

CONFIRMED = "1234.56"  # distinctive active-pledge amount
GOAL = "9000.00"  # distinctive goal


@pytest.fixture
def report_setup(db):
    missionary = User.objects.create_user(
        email="m-jr@example.com",
        password="pw",
        first_name="Mary",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-jr@example.com",
        password="pw",
        first_name="Cora",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    journal = Journal.objects.create(owner=missionary, name="2026 MPD", goal_amount=GOAL)
    contact = Contact.objects.create(
        owner=missionary, first_name="Dana", last_name="Donor", status="donor"
    )
    jc = JournalContact.objects.create(journal=journal, contact=contact)
    Decision.objects.create(
        journal_contact=jc, amount=CONFIRMED, cadence="monthly", status="active"
    )
    return {"missionary": missionary, "coach": coach, "journal": journal}


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestCoachJournalReport:
    def test_coach_report_omits_financial_aggregates(self, report_setup):
        jid = report_setup["journal"].id
        resp = _client(report_setup["coach"]).get(
            f"/api/v1/journals/analytics/journal-report/?journal_id={jid}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert CONFIRMED not in str(resp.data)
        assert GOAL not in str(resp.data)
        assert resp.data["metrics"]["confirmed_amount"] is None
        assert resp.data["goal_amount"] is None
        # Non-financial pipeline metrics still present so the coach can support.
        assert resp.data["metrics"]["total_contacts"] == 1

    def test_missionary_report_includes_financial_aggregates(self, report_setup):
        """Financial role still sees the money figures (no over-gating)."""
        jid = report_setup["journal"].id
        resp = _client(report_setup["missionary"]).get(
            f"/api/v1/journals/analytics/journal-report/?journal_id={jid}"
        )
        assert resp.status_code == status.HTTP_200_OK
        # Decimal serializes with trailing zeros; assert the figure is present.
        assert resp.data["metrics"]["confirmed_amount"] is not None
        assert CONFIRMED in str(resp.data)
        assert resp.data["goal_amount"] is not None
        assert GOAL in str(resp.data)
