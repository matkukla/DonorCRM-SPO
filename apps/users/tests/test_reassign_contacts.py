"""Bulk contact reassignment for offboarding — risk register R7.

When a missionary departs, an admin can reassign all of their contacts to a new
active owner via POST /users/<id>/reassign-contacts/ so the donor relationships
aren't stranded on an inactive account. Admin-only; the new owner must exist,
be active, and differ from the current owner.
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact

User = get_user_model()


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _url(user_id):
    return f"/api/v1/users/{user_id}/reassign-contacts/"


@pytest.fixture
def reassign_setup(db):
    admin = User.objects.create_user(email="admin-rea@example.com", password="pw", role="admin")
    departing = User.objects.create_user(
        email="dep-rea@example.com", password="pw", role="missionary"
    )
    successor = User.objects.create_user(
        email="suc-rea@example.com", password="pw", role="missionary"
    )
    c1 = Contact.objects.create(owner=departing, first_name="A", last_name="One")
    c2 = Contact.objects.create(owner=departing, first_name="B", last_name="Two")
    return {"admin": admin, "departing": departing, "successor": successor, "c1": c1, "c2": c2}


@pytest.mark.django_db
class TestReassignContacts:
    def test_admin_reassigns_all_contacts(self, reassign_setup):
        d = reassign_setup
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["reassigned"] == 2
        d["c1"].refresh_from_db()
        d["c2"].refresh_from_db()
        assert d["c1"].owner_id == d["successor"].id
        assert d["c2"].owner_id == d["successor"].id

    def test_non_admin_forbidden(self, reassign_setup):
        d = reassign_setup
        resp = _client(d["successor"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        d["c1"].refresh_from_db()
        assert d["c1"].owner_id == d["departing"].id

    def test_same_owner_rejected(self, reassign_setup):
        d = reassign_setup
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["departing"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_inactive_new_owner_rejected(self, reassign_setup):
        d = reassign_setup
        d["successor"].is_active = False
        d["successor"].save()
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_new_owner_rejected(self, reassign_setup):
        d = reassign_setup
        resp = _client(d["admin"]).post(_url(d["departing"].id), {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
