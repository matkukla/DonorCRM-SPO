"""Regression tests for the 2026-06-22 report_3 re-scan findings #3 and #7.

A coach (non-financial role) may list/export a coached missionary's journals
but must not receive the fundraising goal_amount (CWE-200):

  #7 — JournalListSerializer must null goal_amount for coaches.
  #3 — the journal CSV export must blank the Goal Amount column for coaches
       (the column stays in the header so the CSV shape is stable).

A missionary (financial role) still sees the goal in both, proving no
over-gating. Each test fails if a gate is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.journals.models import Journal

User = get_user_model()

GOAL = "9000.99"  # distinctive journal goal — must be absent from coach responses


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def journal_setup(db):
    missionary = User.objects.create_user(
        email="m-jg@example.com",
        password="pw",
        first_name="Mary",
        last_name="M",
        role="missionary",
    )
    coach = User.objects.create_user(
        email="c-jg@example.com",
        password="pw",
        first_name="Cora",
        last_name="C",
        role="coach",
    )
    coach.coached_users.add(missionary)
    journal = Journal.objects.create(owner=missionary, name="2026 MPD", goal_amount=GOAL)
    return {"missionary": missionary, "coach": coach, "journal": journal}


def _csv_body(response):
    """Drain a StreamingHttpResponse into a decoded string."""
    return b"".join(response.streaming_content).decode("utf-8")


@pytest.mark.django_db
class TestCoachJournalListGoalLeak:
    """Finding #7 — list endpoint nulls goal_amount for coaches."""

    def test_coach_list_nulls_goal_amount(self, journal_setup):
        resp = _client(journal_setup["coach"]).get("/api/v1/journals/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 1
        assert results[0]["goal_amount"] is None
        assert GOAL not in str(resp.data)

    def test_missionary_list_includes_goal_amount(self, journal_setup):
        """Financial role still sees the goal (no over-gating)."""
        resp = _client(journal_setup["missionary"]).get("/api/v1/journals/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert results[0]["goal_amount"] is not None
        assert GOAL in str(resp.data)


@pytest.mark.django_db
class TestCoachJournalExportGoalLeak:
    """Finding #3 — CSV export blanks the Goal Amount column for coaches."""

    def test_coach_export_omits_goal_amount(self, journal_setup):
        resp = _client(journal_setup["coach"]).get("/api/v1/journals/export/csv/")
        assert resp.status_code == status.HTTP_200_OK
        body = _csv_body(resp)
        # Column header is retained so the CSV shape stays stable...
        assert "Goal Amount" in body
        # ...but the coached user's goal value must be absent.
        assert GOAL not in body

    def test_missionary_export_includes_goal_amount(self, journal_setup):
        """Financial role still sees the goal value in the export."""
        resp = _client(journal_setup["missionary"]).get("/api/v1/journals/export/csv/")
        assert resp.status_code == status.HTTP_200_OK
        body = _csv_body(resp)
        assert GOAL in body
