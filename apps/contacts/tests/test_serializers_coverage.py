"""
Behavioral coverage tests for apps.contacts.serializers.

Covers group assignment on create/update (ContactCreateSerializer and
ContactDetailSerializer via the _visible_groups scoping helper) and the
ContactJournalMembershipSerializer fallback branches (current_stage and
decision computed without prefetch). Tests assert real persisted state and
owner-scoped group visibility so they fail when the serializer logic breaks.
"""

from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.contacts.serializers import ContactJournalMembershipSerializer
from apps.contacts.tests.factories import ContactFactory
from apps.groups.tests.factories import GroupFactory, SharedGroupFactory
from apps.journals.models import (
    Decision,
    Journal,
    JournalContact,
    JournalStageEvent,
    PipelineStage,
    StageEventType,
)
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user():
    return UserFactory(role="missionary")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestContactCreateSerializerGroups:
    """POST /api/v1/contacts/ with group_ids — ContactCreateSerializer.create."""

    def test_create_assigns_owned_group(self, auth_client, user):
        group = GroupFactory(owner=user)
        resp = auth_client.post(
            "/api/v1/contacts/",
            {"first_name": "Grace", "last_name": "Hopper", "group_ids": [str(group.id)]},
            format="json",
        )
        assert resp.status_code == 201
        contact = Contact.objects.get(pk=resp.json()["id"])
        assert list(contact.groups.values_list("id", flat=True)) == [group.id]

    def test_create_assigns_shared_group(self, auth_client, user):
        """Shared groups (owner=None) are visible and assignable."""
        shared = SharedGroupFactory()
        resp = auth_client.post(
            "/api/v1/contacts/",
            {"first_name": "Ada", "last_name": "Lovelace", "group_ids": [str(shared.id)]},
            format="json",
        )
        assert resp.status_code == 201
        contact = Contact.objects.get(pk=resp.json()["id"])
        assert shared.id in set(contact.groups.values_list("id", flat=True))

    def test_create_ignores_other_users_group(self, auth_client, user):
        """A group owned by another user is filtered out (not assigned)."""
        other = UserFactory(role="missionary")
        foreign_group = GroupFactory(owner=other)
        resp = auth_client.post(
            "/api/v1/contacts/",
            {"first_name": "Alan", "last_name": "Turing", "group_ids": [str(foreign_group.id)]},
            format="json",
        )
        assert resp.status_code == 201
        contact = Contact.objects.get(pk=resp.json()["id"])
        # Foreign group must not be attached (security scoping)
        assert contact.groups.count() == 0


@pytest.mark.django_db
class TestContactDetailSerializerGroups:
    """PATCH /api/v1/contacts/{id}/ with group_ids — ContactDetailSerializer.update."""

    def test_update_sets_owned_groups(self, auth_client, user):
        contact = ContactFactory(owner=user)
        group_a = GroupFactory(owner=user)
        group_b = GroupFactory(owner=user)
        resp = auth_client.patch(
            f"/api/v1/contacts/{contact.id}/",
            {"group_ids": [str(group_a.id), str(group_b.id)]},
            format="json",
        )
        assert resp.status_code == 200
        contact.refresh_from_db()
        assert set(contact.groups.values_list("id", flat=True)) == {group_a.id, group_b.id}

    def test_update_replaces_existing_groups(self, auth_client, user):
        contact = ContactFactory(owner=user)
        old = GroupFactory(owner=user)
        new = GroupFactory(owner=user)
        contact.groups.add(old)
        resp = auth_client.patch(
            f"/api/v1/contacts/{contact.id}/",
            {"group_ids": [str(new.id)]},
            format="json",
        )
        assert resp.status_code == 200
        contact.refresh_from_db()
        # .set() replaces — old removed, new present
        assert set(contact.groups.values_list("id", flat=True)) == {new.id}

    def test_update_empty_group_ids_clears_groups(self, auth_client, user):
        contact = ContactFactory(owner=user)
        group = GroupFactory(owner=user)
        contact.groups.add(group)
        resp = auth_client.patch(
            f"/api/v1/contacts/{contact.id}/",
            {"group_ids": []},
            format="json",
        )
        assert resp.status_code == 200
        contact.refresh_from_db()
        # Empty list is not None -> groups cleared
        assert contact.groups.count() == 0

    def test_update_without_group_ids_leaves_groups_untouched(self, auth_client, user):
        contact = ContactFactory(owner=user)
        group = GroupFactory(owner=user)
        contact.groups.add(group)
        resp = auth_client.patch(
            f"/api/v1/contacts/{contact.id}/",
            {"first_name": "Renamed"},
            format="json",
        )
        assert resp.status_code == 200
        contact.refresh_from_db()
        # group_ids omitted (None) -> groups untouched
        assert set(contact.groups.values_list("id", flat=True)) == {group.id}
        assert contact.first_name == "Renamed"

    def test_update_filters_out_foreign_group(self, auth_client, user):
        contact = ContactFactory(owner=user)
        other = UserFactory(role="missionary")
        foreign = GroupFactory(owner=other)
        resp = auth_client.patch(
            f"/api/v1/contacts/{contact.id}/",
            {"group_ids": [str(foreign.id)]},
            format="json",
        )
        assert resp.status_code == 200
        contact.refresh_from_db()
        # Foreign group filtered by _visible_groups -> nothing set
        assert contact.groups.count() == 0


@pytest.mark.django_db
class TestVisibleGroupsUnauthenticated:
    """_visible_groups returns empty when request/user is missing."""

    def test_no_request_returns_no_groups(self, user):
        from apps.contacts.serializers import ContactDetailSerializer

        contact = ContactFactory(owner=user)
        group = GroupFactory(owner=user)
        # Serializer with no request in context -> _visible_groups short-circuits.
        ser = ContactDetailSerializer(
            instance=contact,
            data={"group_ids": [str(group.id)]},
            partial=True,
        )
        assert ser.is_valid(), ser.errors
        ser.save()
        contact.refresh_from_db()
        # No request -> Group.objects.none() -> no groups attached
        assert contact.groups.count() == 0


@pytest.mark.django_db
class TestContactDetailSerializerCreate:
    """ContactDetailSerializer.create assigns groups (direct, since the API
    create endpoint uses ContactCreateSerializer)."""

    def test_create_with_groups(self, user):
        from rest_framework.test import APIRequestFactory

        from apps.contacts.serializers import ContactDetailSerializer

        group = GroupFactory(owner=user)
        request = APIRequestFactory().post("/api/v1/contacts/")
        request.user = user
        ser = ContactDetailSerializer(
            data={"first_name": "Katherine", "last_name": "Johnson", "group_ids": [str(group.id)]},
            context={"request": request},
        )
        assert ser.is_valid(), ser.errors
        contact = ser.save(owner=user)
        assert set(contact.groups.values_list("id", flat=True)) == {group.id}

    def test_create_without_groups(self, user):
        from rest_framework.test import APIRequestFactory

        from apps.contacts.serializers import ContactDetailSerializer

        request = APIRequestFactory().post("/api/v1/contacts/")
        request.user = user
        ser = ContactDetailSerializer(
            data={"first_name": "Dorothy", "last_name": "Vaughan"},
            context={"request": request},
        )
        assert ser.is_valid(), ser.errors
        contact = ser.save(owner=user)
        assert contact.groups.count() == 0


@pytest.mark.django_db
class TestJournalMembershipSerializerFallbacks:
    """ContactJournalMembershipSerializer get_current_stage/get_decision fallbacks
    when events/decisions are NOT prefetched (direct serialization)."""

    def _serialize(self, jc):
        # Re-fetch without the prefetch attributes the view sets, so the
        # serializer hits its query-based fallback branches.
        fresh = JournalContact.objects.get(pk=jc.pk)
        return ContactJournalMembershipSerializer(fresh).data

    def test_current_stage_fallback_from_latest_event(self, user):
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.MEET,
            event_type=StageEventType.MEETING_COMPLETED,
            triggered_by=user,
        )
        data = self._serialize(jc)
        # No prefetched_events attr -> falls back to stage_events query
        assert data["current_stage"] == PipelineStage.MEET

    def test_current_stage_fallback_no_events_defaults_to_contact(self, user):
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        data = self._serialize(jc)
        assert data["current_stage"] == PipelineStage.CONTACT

    def test_decision_fallback_present(self, user):
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        decision = Decision.objects.create(
            journal_contact=jc, amount="125.00", cadence="monthly", status="active"
        )
        data = self._serialize(jc)
        assert data["decision"] is not None
        assert data["decision"]["id"] == str(decision.id)
        assert data["decision"]["amount"] == "125.00"
        assert data["decision"]["cadence"] == "monthly"
        assert data["decision"]["status"] == "active"

    def test_decision_fallback_none(self, user):
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        data = self._serialize(jc)
        assert data["decision"] is None
