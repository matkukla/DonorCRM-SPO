"""
Tests for the Reconnect surface (F6/F7b, ADR 0005):
  - get_reconnect_contacts service (threshold + never-contacted-first ordering)
  - the contact Overview last_touch line via ContactDetailSerializer.
"""

from datetime import timedelta

from django.utils import timezone

from rest_framework.test import APIClient

import pytest

from apps.contacts.models import ContactStatus
from apps.contacts.tests.factories import ContactFactory
from apps.dashboard.services import get_reconnect_contacts
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


@pytest.mark.django_db
class TestGetReconnectContacts:
    def test_includes_stale_and_never_excludes_recent(self):
        user = UserFactory(role="missionary")
        recent = ContactFactory(owner=user, status=ContactStatus.DONOR, first_name="Recent")
        TaskFactory(
            owner=user,
            contact=recent,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=5),
        )
        stale = ContactFactory(owner=user, status=ContactStatus.DONOR, first_name="Stale")
        TaskFactory(
            owner=user,
            contact=stale,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=120),
        )
        never = ContactFactory(owner=user, status=ContactStatus.LAPSED, first_name="Never")

        rows = get_reconnect_contacts(user)
        ids = [r["contact_id"] for r in rows]

        assert str(stale.id) in ids
        assert str(never.id) in ids
        assert str(recent.id) not in ids

    def test_never_contacted_sorts_first(self):
        user = UserFactory(role="missionary")
        stale = ContactFactory(owner=user, status=ContactStatus.DONOR)
        TaskFactory(
            owner=user,
            contact=stale,
            task_type=TaskType.MEETING,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=120),
        )
        never = ContactFactory(owner=user, status=ContactStatus.DONOR)

        rows = get_reconnect_contacts(user)
        ids = [r["contact_id"] for r in rows]

        assert ids.index(str(never.id)) < ids.index(str(stale.id))
        never_row = next(r for r in rows if r["contact_id"] == str(never.id))
        assert never_row["last_contacted"] is None
        assert never_row["days_since_contact"] is None

    def test_excludes_non_donor_statuses(self):
        user = UserFactory(role="missionary")
        prospect = ContactFactory(owner=user, status=ContactStatus.PROSPECT)

        rows = get_reconnect_contacts(user)

        assert str(prospect.id) not in [r["contact_id"] for r in rows]


@pytest.mark.django_db
class TestReconnectView:
    def test_endpoint_returns_reconnect_contacts(self):
        user = UserFactory(role="missionary")
        ContactFactory(owner=user, status=ContactStatus.DONOR)
        client = APIClient()
        client.force_authenticate(user=user)

        resp = client.get("/api/v1/dashboard/reconnect/")

        assert resp.status_code == 200
        assert "reconnect_contacts" in resp.data
        assert resp.data["total_count"] == len(resp.data["reconnect_contacts"])


@pytest.mark.django_db
class TestContactLastTouchSerializer:
    def _detail(self, client, contact):
        resp = client.get(f"/api/v1/contacts/{contact.id}/")
        assert resp.status_code == 200
        return resp.data

    def test_last_touch_reflects_call_task(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        TaskFactory(
            owner=user,
            contact=contact,
            task_type=TaskType.CALL,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now() - timedelta(days=4),
        )
        client = APIClient()
        client.force_authenticate(user=user)

        data = self._detail(client, contact)
        assert data["last_touch"]["type"] == "call"
        assert data["last_touch"]["at"] is not None

    def test_last_touch_reflects_meeting_event(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.MEET,
            event_type=StageEventType.MEETING_COMPLETED,
            triggered_by=user,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        data = self._detail(client, contact)
        assert data["last_touch"]["type"] == "meeting"
        assert data["last_touch"]["at"] is not None

    def test_last_touch_null_when_no_logged_contact(self):
        user = UserFactory(role="missionary")
        contact = ContactFactory(owner=user)
        client = APIClient()
        client.force_authenticate(user=user)

        data = self._detail(client, contact)
        assert data["last_touch"]["at"] is None
        assert data["last_touch"]["type"] is None
