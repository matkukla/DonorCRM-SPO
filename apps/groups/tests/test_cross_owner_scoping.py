"""Shared-group cross-owner contact/email scoping — security report #1/#2.

A user with visibility to a shared group could list every contact (and email)
attached to it, including contacts owned by other users (CWE-639). The group
contacts/emails endpoints now scope to the requester's visible owners.

Each test fails if the owner filter is reverted (project rule #1).
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
    """Two missionaries each own a contact; both are in one shared group."""
    user_a = User.objects.create_user(
        email="a-grp@example.com", password="pw", first_name="Amy", last_name="A", role="missionary"
    )
    user_b = User.objects.create_user(
        email="b-grp@example.com", password="pw", first_name="Ben", last_name="B", role="missionary"
    )
    contact_a = Contact.objects.create(
        owner=user_a, first_name="Dana", last_name="DonorA", email="dana.a@example.com"
    )
    contact_b = Contact.objects.create(
        owner=user_b, first_name="Eli", last_name="DonorB", email="eli.b@example.com"
    )
    group = Group.objects.create(name="Shared", owner=None)  # shared (visible to all)
    group.contacts.add(contact_a, contact_b)
    return {
        "a": user_a,
        "b": user_b,
        "contact_a": contact_a,
        "contact_b": contact_b,
        "group": group,
    }


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestSharedGroupScoping:
    def test_contacts_endpoint_hides_other_owners_contact(self, shared_group_setup):
        gid = shared_group_setup["group"].id
        resp = _client(shared_group_setup["b"]).get(f"/api/v1/groups/{gid}/contacts/")
        assert resp.status_code == status.HTTP_200_OK
        returned_ids = {row["id"] for row in resp.data}
        assert str(shared_group_setup["contact_b"].id) in returned_ids
        assert str(shared_group_setup["contact_a"].id) not in returned_ids

    def test_emails_endpoint_hides_other_owners_email(self, shared_group_setup):
        gid = shared_group_setup["group"].id
        resp = _client(shared_group_setup["b"]).get(f"/api/v1/groups/{gid}/contacts/emails/")
        assert resp.status_code == status.HTTP_200_OK
        assert "eli.b@example.com" in resp.data["emails"]
        assert "dana.a@example.com" not in resp.data["emails"]

    def test_owner_still_sees_own_contact(self, shared_group_setup):
        gid = shared_group_setup["group"].id
        resp = _client(shared_group_setup["a"]).get(f"/api/v1/groups/{gid}/contacts/")
        assert resp.status_code == status.HTTP_200_OK
        returned_ids = {row["id"] for row in resp.data}
        assert str(shared_group_setup["contact_a"].id) in returned_ids
        assert str(shared_group_setup["contact_b"].id) not in returned_ids
