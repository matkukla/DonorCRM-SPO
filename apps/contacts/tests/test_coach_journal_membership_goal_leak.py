"""Regression test for the pilot-readiness coach goal_amount leak.

A coach (non-financial role) may list a coached missionary's journal
memberships via the contact "Journals" tab (GET /contacts/<id>/journals/),
but must not receive the fundraising goal_amount (CWE-200). This mirrors the
gating already enforced on JournalListSerializer (report_3 finding #7); the
sibling ContactJournalMembershipSerializer originally missed it.

A missionary (financial role) still sees the goal, proving no over-gating.
Each test fails if the gate is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.journals.models import Journal, JournalContact

User = get_user_model()

GOAL = "7777.77"  # distinctive journal goal — must be absent from coach responses


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def membership_setup(db):
    missionary = User.objects.create_user(
        email="m-jcg@example.com",
        password="pw",
        first_name="Mara",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-jcg@example.com",
        password="pw",
        first_name="Cole",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    contact = Contact.objects.create(
        owner=missionary,
        first_name="Dana",
        last_name="Donor",
        status="donor",
    )
    journal = Journal.objects.create(owner=missionary, name="2026 MPD", goal_amount=GOAL)
    JournalContact.objects.create(journal=journal, contact=contact)
    return {"missionary": missionary, "coach": coach, "contact": contact}


@pytest.mark.django_db
class TestCoachContactJournalsGoalLeak:
    def test_coach_membership_nulls_goal_amount(self, membership_setup):
        cid = membership_setup["contact"].id
        resp = _client(membership_setup["coach"]).get(f"/api/v1/contacts/{cid}/journals/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["goal_amount"] is None
        assert GOAL not in str(resp.data)

    def test_missionary_membership_includes_goal_amount(self, membership_setup):
        """Financial role still sees the goal (no over-gating)."""
        cid = membership_setup["contact"].id
        resp = _client(membership_setup["missionary"]).get(f"/api/v1/contacts/{cid}/journals/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["goal_amount"] is not None
        assert GOAL in str(resp.data)
