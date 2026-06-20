"""Coach financial gating for pledge (Decision) data — PRD fix #1.

A coach is NOT a financial role (apps/core/permissions.is_financial_role) and must
never receive individual pledge amounts. These tests assert at the HTTP API that:

  - the Decision list / detail / history endpoints return nothing to a coach, and
  - the two serializers that embed a decision summary (journal-member list,
    contact-journals) omit the pledge amount / monthly_equivalent for a coach while
    still returning pipeline status + cadence.

A missionary (financial role) still sees the amount everywhere — guards against
over-gating. Each test fails if its guard is reverted (project rule #1).

The distinctive pledge amount 1234.56 is greppable: it must never appear in a coach
response body.
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.journals.models import Decision, DecisionHistory, Journal, JournalContact

User = get_user_model()

PLEDGE_AMOUNT = "1234.56"  # distinctive — must be absent from any coach response body
HISTORY_AMOUNT = "1199.88"  # distinctive prior amount recorded in decision history


@pytest.fixture
def gating_setup(db):
    """Coach C coaches missionary M, who has one active pledge of $1,234.56."""
    missionary = User.objects.create_user(
        email="m-gating@example.com",
        password="pw",
        first_name="Mary",
        last_name="Missionary",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-gating@example.com",
        password="pw",
        first_name="Cora",
        last_name="Coach",
        role="coach",
    )
    coach.coached_users.add(missionary)

    journal = Journal.objects.create(owner=missionary, name="2026 MPD", goal_amount=50000.00)
    contact = Contact.objects.create(
        owner=missionary,
        first_name="Dana",
        last_name="Donor",
        email="dana.donor@example.com",
        status="donor",
    )
    jc = JournalContact.objects.create(journal=journal, contact=contact)
    decision = Decision.objects.create(
        journal_contact=jc,
        amount=PLEDGE_AMOUNT,
        cadence="monthly",
        status="active",
    )
    DecisionHistory.objects.create(
        decision=decision,
        changed_by=missionary,
        changed_fields={"amount": {"old": HISTORY_AMOUNT, "new": PLEDGE_AMOUNT}},
    )
    return {
        "missionary": missionary,
        "coach": coach,
        "journal": journal,
        "contact": contact,
        "jc": jc,
        "decision": decision,
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestCoachPledgeGating:
    def test_coach_decisions_list_is_empty(self, gating_setup):
        resp = _client(gating_setup["coach"]).get("/api/v1/journals/decisions/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 0
        assert PLEDGE_AMOUNT not in str(resp.data)

    def test_coach_decision_detail_not_found(self, gating_setup):
        did = gating_setup["decision"].id
        resp = _client(gating_setup["coach"]).get(f"/api/v1/journals/decisions/{did}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_coach_decision_history_is_empty(self, gating_setup):
        resp = _client(gating_setup["coach"]).get("/api/v1/journals/decision-history/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 0
        assert HISTORY_AMOUNT not in str(resp.data)
        assert PLEDGE_AMOUNT not in str(resp.data)

    def test_missionary_sees_decision_history(self, gating_setup):
        """Financial role still sees prior pledge amounts in history (no over-gating)."""
        resp = _client(gating_setup["missionary"]).get("/api/v1/journals/decision-history/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert HISTORY_AMOUNT in str(resp.data)

    def test_coach_journal_member_list_omits_amount_keeps_status(self, gating_setup):
        journal_id = gating_setup["journal"].id
        resp = _client(gating_setup["coach"]).get(
            f"/api/v1/journals/journal-members/?journal_id={journal_id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert PLEDGE_AMOUNT not in str(resp.data)
        # Pipeline status/cadence still present so the coach can support the pipeline.
        member = resp.data["results"][0] if "results" in resp.data else resp.data[0]
        decision = member["decision"]
        assert decision is not None
        assert decision["status"] == "active"
        assert decision["cadence"] == "monthly"
        assert "amount" not in decision
        assert "monthly_equivalent" not in decision

    def test_coach_contact_journals_omits_amount_keeps_status(self, gating_setup):
        contact_id = gating_setup["contact"].id
        resp = _client(gating_setup["coach"]).get(f"/api/v1/contacts/{contact_id}/journals/")
        assert resp.status_code == status.HTTP_200_OK
        assert PLEDGE_AMOUNT not in str(resp.data)
        body = (
            resp.data["results"]
            if isinstance(resp.data, dict) and "results" in resp.data
            else resp.data
        )
        decision = body[0]["decision"]
        assert decision is not None
        assert decision["status"] == "active"
        assert "amount" not in decision

    def test_missionary_still_sees_pledge_amount(self, gating_setup):
        """Financial role is unaffected — no over-gating."""
        resp = _client(gating_setup["missionary"]).get("/api/v1/journals/decisions/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert PLEDGE_AMOUNT in str(resp.data)

    def test_missionary_journal_member_includes_amount(self, gating_setup):
        journal_id = gating_setup["journal"].id
        resp = _client(gating_setup["missionary"]).get(
            f"/api/v1/journals/journal-members/?journal_id={journal_id}"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert PLEDGE_AMOUNT in str(resp.data)
