"""Journal stage-event write ownership — PRD fix #6.

The stage-event serializer must reject a journal_contact that does not belong to the
requester (unless admin), mirroring DecisionSerializer / NextStepSerializer. Without
this, a missionary can POST a stage event onto another missionary's pipeline.

Each test fails if the guard is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.journals.models import Journal, JournalContact, JournalStageEvent

User = get_user_model()

STAGE_EVENTS_URL = "/api/v1/journals/stage-events/"


def _jc_for(owner):
    journal = Journal.objects.create(owner=owner, name="J", goal_amount=1000)
    contact = Contact.objects.create(
        owner=owner, first_name="C", last_name="One", email=f"{owner.email}-c@example.com"
    )
    return JournalContact.objects.create(journal=journal, contact=contact)


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _payload(jc):
    return {
        "journal_contact": str(jc.id),
        "stage": "contact",
        "event_type": "call_logged",
        "notes": "x",
    }


@pytest.mark.django_db
class TestStageEventWriteOwnership:
    def test_missionary_cannot_write_stage_event_on_others_journal_contact(self):
        a = User.objects.create_user(email="a-se@example.com", password="pw", role="missionary")
        b = User.objects.create_user(email="b-se@example.com", password="pw", role="missionary")
        jc_b = _jc_for(b)

        resp = _client(a).post(STAGE_EVENTS_URL, _payload(jc_b), format="json")

        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN)
        assert not JournalStageEvent.objects.filter(journal_contact=jc_b).exists()

    def test_missionary_can_write_stage_event_on_own_journal_contact(self):
        a = User.objects.create_user(email="a2-se@example.com", password="pw", role="missionary")
        jc_a = _jc_for(a)

        resp = _client(a).post(STAGE_EVENTS_URL, _payload(jc_a), format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        assert JournalStageEvent.objects.filter(journal_contact=jc_a).exists()

    def test_admin_can_write_stage_event_on_any_journal_contact(self):
        admin = User.objects.create_user(email="admin-se@example.com", password="pw", role="admin")
        missionary = User.objects.create_user(
            email="m3-se@example.com", password="pw", role="missionary"
        )
        jc_m = _jc_for(missionary)

        resp = _client(admin).post(STAGE_EVENTS_URL, _payload(jc_m), format="json")

        assert resp.status_code == status.HTTP_201_CREATED
