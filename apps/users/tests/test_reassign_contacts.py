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
from apps.groups.models import Group
from apps.journals.models import Journal
from apps.tasks.models import BroadcastTask, Task

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


@pytest.mark.django_db
class TestReassignMovesOwnedHistory:
    """Reassignment must move the departing user's Journal and Task ownership,
    not just Contact.owner. Journals and Tasks carry their own owner FK — the
    field every view scopes by — so leaving them on the departing user strands
    donor pipeline history and open follow-up tasks (issue #185).
    """

    def test_reassigns_journal_ownership(self, reassign_setup):
        d = reassign_setup
        journal = Journal.objects.create(
            owner=d["departing"], name="Q1 Campaign", goal_amount="1000.00"
        )
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        journal.refresh_from_db()
        assert journal.owner_id == d["successor"].id
        assert resp.data["journals_reassigned"] == 1

    def test_reassigns_task_ownership(self, reassign_setup):
        d = reassign_setup
        task = Task.objects.create(
            owner=d["departing"],
            contact=d["c1"],
            title="Follow up",
            due_date="2026-01-01",
        )
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.owner_id == d["successor"].id
        assert resp.data["tasks_reassigned"] == 1

    def test_broadcast_copies_are_not_reassigned(self, reassign_setup):
        """A broadcast copy is a recipient-owned distribution (issue #184), not
        donor history that follows the contact. It must stay with its recipient.
        """
        d = reassign_setup
        broadcast = BroadcastTask.objects.create(
            sender=d["admin"],
            title="All-hands",
            due_date="2026-01-01",
            target_type="all_missionaries",
        )
        copy = Task.objects.create(
            owner=d["departing"],
            title="All-hands",
            due_date="2026-01-01",
            broadcast=broadcast,
        )
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        copy.refresh_from_db()
        assert copy.owner_id == d["departing"].id
        assert resp.data["tasks_reassigned"] == 0

    def test_reassigns_private_group_ownership(self, reassign_setup):
        d = reassign_setup
        group = Group.objects.create(owner=d["departing"], name="Major Donors")
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        group.refresh_from_db()
        assert group.owner_id == d["successor"].id
        assert resp.data["groups_reassigned"] == 1

    def test_org_wide_group_is_not_reassigned(self, reassign_setup):
        """Shared groups (owner=None) belong to no one and must stay shared."""
        d = reassign_setup
        shared = Group.objects.create(owner=None, name="Org Segment")
        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        shared.refresh_from_db()
        assert shared.owner_id is None

    def test_group_name_collision_is_skipped_not_crashed(self, reassign_setup):
        """unique_group_name_per_owner: if the successor already has a same-named
        group, skip the departing user's copy rather than crashing the whole
        reassignment on an IntegrityError.
        """
        d = reassign_setup
        # Both users have a "VIPs" group — a naive bulk update would collide.
        dep_vips = Group.objects.create(owner=d["departing"], name="VIPs")
        Group.objects.create(owner=d["successor"], name="VIPs")
        dep_unique = Group.objects.create(owner=d["departing"], name="Prospects")

        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        # Non-colliding group moved; contacts still moved too.
        dep_unique.refresh_from_db()
        assert dep_unique.owner_id == d["successor"].id
        # Colliding group left behind rather than blowing up the transaction.
        dep_vips.refresh_from_db()
        assert dep_vips.owner_id == d["departing"].id
        assert resp.data["groups_reassigned"] == 1
        # The reassignment as a whole still succeeded.
        d["c1"].refresh_from_db()
        assert d["c1"].owner_id == d["successor"].id

    def test_reassignment_is_atomic_across_models(self, reassign_setup):
        """Contacts, journals, tasks, and private groups all move together."""
        d = reassign_setup
        Journal.objects.create(owner=d["departing"], name="Camp", goal_amount="500.00")
        Task.objects.create(
            owner=d["departing"], contact=d["c1"], title="Call", due_date="2026-01-01"
        )
        Group.objects.create(owner=d["departing"], name="Segment")
        # Data owned by an unrelated user must be untouched.
        other = User.objects.create_user(
            email="other-rea@example.com", password="pw", role="missionary"
        )
        other_journal = Journal.objects.create(owner=other, name="Other", goal_amount="500.00")

        resp = _client(d["admin"]).post(
            _url(d["departing"].id), {"new_owner_id": str(d["successor"].id)}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert Journal.objects.filter(owner=d["departing"]).count() == 0
        assert Task.objects.filter(owner=d["departing"]).count() == 0
        assert Group.objects.filter(owner=d["departing"]).count() == 0
        other_journal.refresh_from_db()
        assert other_journal.owner_id == other.id
