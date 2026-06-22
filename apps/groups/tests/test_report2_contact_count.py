"""Regression test for the 2026-06-22 re-scan finding #13.

A shared group (owner=None) can hold contacts owned by multiple users. The
list/detail contact_count annotation counted ALL members, leaking how many
hidden contacts a user could not see (CWE-200). The count must be scoped to the
requester's visible, non-merged contacts — matching GroupContactsView.

Each test fails if the scoped Count filter is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.groups.models import Group

User = get_user_model()


@pytest.fixture
def shared_group_setup(db):
    """Shared group with one contact owned by `viewer` and one hidden contact."""
    viewer = User.objects.create_user(
        email="viewer-grp@example.com",
        password="pw",
        first_name="Vic",
        last_name="Viewer",
        role="missionary",
    )
    other = User.objects.create_user(
        email="other-grp@example.com",
        password="pw",
        first_name="Otto",
        last_name="Other",
        role="missionary",
    )
    group = Group.objects.create(owner=None, name="Org-wide Shared")
    visible_contact = Contact.objects.create(
        owner=viewer, first_name="Vis", last_name="Ible", status="donor"
    )
    hidden_contact = Contact.objects.create(
        owner=other, first_name="Hid", last_name="Den", status="donor"
    )
    group.contacts.add(visible_contact, hidden_contact)
    return {"viewer": viewer, "group": group}


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestSharedGroupContactCount:
    def test_list_count_excludes_hidden_members(self, shared_group_setup):
        resp = _client(shared_group_setup["viewer"]).get("/api/v1/groups/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data["results"] if "results" in resp.data else resp.data
        group = next(g for g in results if g["id"] == str(shared_group_setup["group"].id))
        # Only the viewer's own contact is counted, not the hidden one.
        assert group["contact_count"] == 1
