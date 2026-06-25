"""
Tests for the "Last Contacted" signal (ADR 0005) through the contacts list API.

Last Contacted = max(completed Call/Meeting task.completed_at,
                     call/meeting JournalStageEvent.created_at).
It ignores gifts and non-call/meeting task types, and may be null.

The "Not Contacted Recently" surface filters on this annotation and includes
never-contacted (null) contacts. These tests assert behavior at the API seam so
they fail when a real user would see the feature broken.
"""

from datetime import timedelta

from django.utils import timezone

from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory
from apps.journals.models import (
    Journal,
    JournalContact,
    JournalStageEvent,
    PipelineStage,
    StageEventType,
)
from apps.tasks.models import TaskStatus, TaskType
from apps.tasks.tests.factories import TaskFactory
from apps.users.tests.factories import UserFactory

LIST_URL = "/api/v1/contacts/"


@pytest.fixture
def user():
    return UserFactory(role="missionary")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _row_for(resp, contact):
    for row in resp.data["results"]:
        if row["id"] == str(contact.id):
            return row
    raise AssertionError(f"contact {contact.id} not in results")


@pytest.mark.django_db
class TestLastContactedAnnotation:
    def test_completed_call_task_sets_last_contacted(self, auth_client, user):
        contact = ContactFactory(owner=user)
        when = timezone.now() - timedelta(days=2)
        TaskFactory(
            owner=user,
            contact=contact,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=when,
        )

        resp = auth_client.get(LIST_URL)

        assert resp.status_code == 200
        assert _row_for(resp, contact)["last_contacted"] is not None

    def test_journal_meeting_event_sets_last_contacted(self, auth_client, user):
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.MEET,
            event_type=StageEventType.MEETING_COMPLETED,
            triggered_by=user,
        )

        resp = auth_client.get(LIST_URL)

        assert _row_for(resp, contact)["last_contacted"] is not None

    def test_last_contacted_is_max_of_both_sources(self, auth_client, user):
        contact = ContactFactory(owner=user)
        old_task_at = timezone.now() - timedelta(days=30)
        TaskFactory(
            owner=user,
            contact=contact,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=old_task_at,
        )
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        recent_event = JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.CONTACT,
            event_type=StageEventType.CALL_LOGGED,
            triggered_by=user,
        )

        resp = auth_client.get(LIST_URL)
        last = _row_for(resp, contact)["last_contacted"]

        # The newer journal event wins over the older task.
        assert last is not None
        assert abs(
            timezone.datetime.fromisoformat(last.replace("Z", "+00:00")) - recent_event.created_at
        ) < timedelta(seconds=2)

    def test_ignores_gifts_and_non_call_meeting_tasks(self, auth_client, user):
        contact = ContactFactory(owner=user)
        # A gift is money, not contact.
        GiftFactory(donor_contact=contact, amount_cents=5000, gift_date=timezone.now().date())
        # A completed thank-you task is not a conversation.
        TaskFactory(
            owner=user,
            contact=contact,
            task_type=TaskType.THANK_YOU,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now(),
        )
        # A pending (not completed) call does not count either.
        TaskFactory(
            owner=user,
            contact=contact,
            task_type=TaskType.CALL,
            status=TaskStatus.PENDING,
        )

        resp = auth_client.get(LIST_URL)

        assert _row_for(resp, contact)["last_contacted"] is None

    def test_never_contacted_is_null(self, auth_client, user):
        contact = ContactFactory(owner=user)
        resp = auth_client.get(LIST_URL)
        assert _row_for(resp, contact)["last_contacted"] is None


@pytest.mark.django_db
class TestNotContactedRecentlyFilter:
    def test_filter_returns_stale_and_never_contacted_only(self, auth_client, user):
        # Recently contacted (3 days ago) — should be EXCLUDED.
        recent = ContactFactory(owner=user, first_name="Recent")
        TaskFactory(
            owner=user,
            contact=recent,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=3),
        )
        # Stale (90 days ago) — should be INCLUDED.
        stale = ContactFactory(owner=user, first_name="Stale")
        TaskFactory(
            owner=user,
            contact=stale,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=90),
        )
        # Never contacted — should be INCLUDED (most neglected).
        never = ContactFactory(owner=user, first_name="Never")

        cutoff = (timezone.now() - timedelta(days=60)).isoformat()
        resp = auth_client.get(LIST_URL, {"last_contacted_before": cutoff})

        ids = {row["id"] for row in resp.data["results"]}
        assert str(stale.id) in ids
        assert str(never.id) in ids
        assert str(recent.id) not in ids

    def test_never_contacted_sorts_first_with_last_contacted_ordering(self, auth_client, user):
        never = ContactFactory(owner=user, first_name="Never")
        contacted = ContactFactory(owner=user, first_name="Contacted")
        TaskFactory(
            owner=user,
            contact=contacted,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=90),
        )

        resp = auth_client.get(LIST_URL, {"ordering": "last_contacted"})

        ordered_ids = [row["id"] for row in resp.data["results"]]
        # Never-contacted (null) must come before the contacted donor.
        assert ordered_ids.index(str(never.id)) < ordered_ids.index(str(contacted.id))

    def test_multi_field_ordering_preserves_secondary_sort(self, auth_client, user):
        # Two never-contacted donors: with a secondary last_name sort they must
        # come back alphabetically, proving the secondary key isn't dropped.
        ContactFactory(owner=user, first_name="A", last_name="Adams")
        ContactFactory(owner=user, first_name="B", last_name="Baker")

        resp = auth_client.get(LIST_URL, {"ordering": "last_contacted,last_name"})

        names = [row["last_name"] for row in resp.data["results"]]
        assert names == ["Adams", "Baker"]
