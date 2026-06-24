"""Donor delete-on-request (DSAR / right-to-erasure) — risk register R4.

An admin can hard-delete a donor and all related data (gifts, prayers, tasks,
journal memberships) via POST /contacts/<id>/erase/. Non-admins cannot. Cascade
is enforced at the database (all FKs to Contact are on_delete=CASCADE). The
DataAccessLog is intentionally retained — it references the contact by internal
ID only and holds no PII (data-retention.md).
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.gifts.models import Gift
from apps.journals.models import Journal, JournalContact
from apps.prayers.models import PrayerIntention
from apps.tasks.models import Task

User = get_user_model()


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def erase_setup(db):
    missionary = User.objects.create_user(
        email="m-erase@example.com", password="pw", role="missionary"
    )
    admin = User.objects.create_user(email="admin-erase@example.com", password="pw", role="admin")
    coach = User.objects.create_user(email="coach-erase@example.com", password="pw", role="coach")
    contact = Contact.objects.create(
        owner=missionary, first_name="Erase", last_name="Me", status="donor"
    )
    Gift.objects.create(donor_contact=contact, amount_cents=5000, gift_date=date.today())
    PrayerIntention.objects.create(contact=contact, title="Pray for them")
    Task.objects.create(owner=missionary, contact=contact, title="Follow up", due_date=date.today())
    journal = Journal.objects.create(owner=missionary, name="J", goal_amount="100.00")
    JournalContact.objects.create(journal=journal, contact=contact)
    return {"missionary": missionary, "admin": admin, "coach": coach, "contact": contact}


@pytest.mark.django_db
class TestContactErase:
    def test_admin_erases_donor_and_cascades(self, erase_setup):
        cid = erase_setup["contact"].id
        resp = _client(erase_setup["admin"]).post(f"/api/v1/contacts/{cid}/erase/")
        assert resp.status_code == status.HTTP_200_OK
        assert not Contact.objects.filter(id=cid).exists()
        assert not Gift.objects.filter(donor_contact_id=cid).exists()
        assert not PrayerIntention.objects.filter(contact_id=cid).exists()
        assert not Task.objects.filter(contact_id=cid).exists()
        assert not JournalContact.objects.filter(contact_id=cid).exists()
        assert resp.data["deleted"]["gifts"] == 1

    def test_owner_missionary_cannot_erase(self, erase_setup):
        cid = erase_setup["contact"].id
        resp = _client(erase_setup["missionary"]).post(f"/api/v1/contacts/{cid}/erase/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert Contact.objects.filter(id=cid).exists()

    def test_coach_cannot_erase(self, erase_setup):
        cid = erase_setup["contact"].id
        resp = _client(erase_setup["coach"]).post(f"/api/v1/contacts/{cid}/erase/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert Contact.objects.filter(id=cid).exists()

    def test_erase_nonexistent_returns_404(self, erase_setup):
        resp = _client(erase_setup["admin"]).post(
            "/api/v1/contacts/00000000-0000-0000-0000-000000000000/erase/"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
