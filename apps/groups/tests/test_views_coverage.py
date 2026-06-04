"""
Coverage-focused behavioral tests for apps.groups.views.

Targets the branches the existing test_views.py leaves uncovered:
  - system-group protection on delete / membership mutation
  - not-found and empty-payload error paths
  - admin-with-global-visibility removal branch
  - GroupContactEmailsView (entirely untested before)
"""
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.groups.models import Group
from apps.groups.tests.factories import GroupFactory, SystemGroupFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestGroupDetailDestroy:
    """System-group protection on the detail destroy endpoint."""

    def test_cannot_delete_system_group(self):
        """Deleting a system group is rejected with 400 and the group survives."""
        user = UserFactory(role="admin")
        group = SystemGroupFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(f"/api/v1/groups/{group.id}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "System groups cannot be deleted."
        assert Group.objects.filter(id=group.id).exists()


@pytest.mark.django_db
class TestGroupContactsErrorPaths:
    """Not-found, system-group, and empty-payload paths for membership mutation."""

    def test_get_contacts_group_not_found(self):
        """GET on a group the user cannot see returns 404."""
        owner = UserFactory(role="missionary")
        other = UserFactory(role="missionary")
        group = GroupFactory(owner=owner)

        client = APIClient()
        client.force_authenticate(user=other)

        response = client.get(f"/api/v1/groups/{group.id}/contacts/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Group not found."

    def test_post_to_system_group_rejected(self):
        """Adding contacts to a system group is blocked with 400."""
        user = UserFactory(role="missionary")
        group = SystemGroupFactory(owner=user)
        contact = ContactFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f"/api/v1/groups/{group.id}/contacts/",
            {"contact_ids": [str(contact.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Cannot modify membership of system groups."
        assert contact not in group.contacts.all()

    def test_post_without_contact_ids_rejected(self):
        """POST with an empty contact_ids list returns a 400 validation error."""
        user = UserFactory(role="missionary")
        group = GroupFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f"/api/v1/groups/{group.id}/contacts/",
            {"contact_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "No contact_ids provided."

    def test_post_to_missing_group_returns_404(self):
        """POST to a non-existent group id returns 404."""
        import uuid

        user = UserFactory(role="missionary")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f"/api/v1/groups/{uuid.uuid4()}/contacts/",
            {"contact_ids": [str(uuid.uuid4())]},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_to_missing_group_returns_404(self):
        """DELETE to a non-existent group id returns 404."""
        import uuid

        user = UserFactory(role="missionary")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(
            f"/api/v1/groups/{uuid.uuid4()}/contacts/",
            {"contact_ids": [str(uuid.uuid4())]},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_from_system_group_rejected(self):
        """Removing contacts from a system group is blocked with 400."""
        user = UserFactory(role="missionary")
        group = SystemGroupFactory(owner=user)
        contact = ContactFactory(owner=user)
        contact.groups.add(group)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(
            f"/api/v1/groups/{group.id}/contacts/",
            {"contact_ids": [str(contact.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Cannot modify membership of system groups."
        # The system-group guard runs before removal, so membership is unchanged.
        assert contact in group.contacts.all()

    def test_delete_without_contact_ids_rejected(self):
        """DELETE with an empty contact_ids list returns a 400 validation error."""
        user = UserFactory(role="missionary")
        group = GroupFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(
            f"/api/v1/groups/{group.id}/contacts/",
            {"contact_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "No contact_ids provided."


@pytest.mark.django_db
class TestGroupContactsRemoval:
    """Owner-scoped removal of contacts from a group via DELETE."""

    def test_admin_removes_own_contact_from_group(self):
        """An admin can remove their own contact from a group (owner-scoped path)."""
        admin = UserFactory(role="admin")
        group = GroupFactory(owner=admin)
        contact = ContactFactory(owner=admin)
        contact.groups.add(group)
        assert contact in group.contacts.all()

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.delete(
            f"/api/v1/groups/{group.id}/contacts/",
            {"contact_ids": [str(contact.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert contact not in group.contacts.all()

    def test_remove_other_users_contact_is_noop(self):
        """A missionary's DELETE for another owner's contact removes nothing (owner-scoped).

        Returns 200 with a generic message but leaves the membership intact, since
        the contact is not in the caller's visible set.
        """
        owner = UserFactory(role="missionary")
        other = UserFactory(role="missionary")
        group = GroupFactory(owner=other)
        contact = ContactFactory(owner=owner)
        contact.groups.add(group)

        client = APIClient()
        client.force_authenticate(user=other)

        response = client.delete(
            f"/api/v1/groups/{group.id}/contacts/",
            {"contact_ids": [str(contact.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        # Not visible to `other`, so it is NOT removed.
        assert contact in group.contacts.all()


@pytest.mark.django_db
class TestGroupContactEmailsView:
    """The group contact-emails export endpoint."""

    def test_returns_group_contact_emails_with_count(self):
        """Returns every in-group contact email plus a matching count.

        NOTE: order is not asserted. The Contact.email column is encrypted at
        rest, so the view's order_by('email') sorts by ciphertext rather than
        plaintext (see bug report). We assert the set + count, which is the
        correct behavioral contract regardless of ordering.
        """
        user = UserFactory(role="missionary")
        group = GroupFactory(owner=user)
        c1 = ContactFactory(owner=user, email="zed@example.com")
        c2 = ContactFactory(owner=user, email="amy@example.com")
        c1.groups.add(group)
        c2.groups.add(group)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/groups/{group.id}/contacts/emails/")

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data["emails"]) == {"amy@example.com", "zed@example.com"}
        assert response.data["count"] == 2

    def test_excludes_blank_and_null_emails(self):
        """Contacts with empty-string emails are excluded from the export."""
        user = UserFactory(role="missionary")
        group = GroupFactory(owner=user)
        with_email = ContactFactory(owner=user, email="real@example.com")
        blank_email = ContactFactory(owner=user, email="")
        with_email.groups.add(group)
        blank_email.groups.add(group)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/groups/{group.id}/contacts/emails/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["emails"] == ["real@example.com"]
        assert response.data["count"] == 1

    def test_group_not_found_returns_404(self):
        """Requesting emails for an invisible group returns 404, not the data."""
        owner = UserFactory(role="missionary")
        other = UserFactory(role="missionary")
        group = GroupFactory(owner=owner)

        client = APIClient()
        client.force_authenticate(user=other)

        response = client.get(f"/api/v1/groups/{group.id}/contacts/emails/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Group not found."

    def test_unauthenticated_rejected(self):
        """Anonymous access to the emails endpoint is rejected with 401."""
        group = GroupFactory()
        client = APIClient()

        response = client.get(f"/api/v1/groups/{group.id}/contacts/emails/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
