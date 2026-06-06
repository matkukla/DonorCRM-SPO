"""
Behavioral coverage tests for prayer intention views and serializer.

Exercises CRUD, owner-scoping, status-timestamp management, mark-prayed,
and today's-focus rotation. Each test asserts real behavior so it fails
when the feature breaks.
"""

from datetime import timedelta

from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.prayers.models import PrayerIntention
from apps.users.tests.factories import UserFactory

LIST_URL = "/api/v1/prayers/"
FOCUS_URL = "/api/v1/prayers/focus/"


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _detail_url(pk):
    return f"/api/v1/prayers/{pk}/"


def _prayed_url(pk):
    return f"/api/v1/prayers/{pk}/prayed/"


@pytest.fixture
def missionary():
    return UserFactory(role="missionary", email="prayer-owner@test.com")


@pytest.fixture
def other_missionary():
    return UserFactory(role="missionary", email="prayer-other@test.com")


@pytest.fixture
def owned_contact(missionary):
    return ContactFactory(owner=missionary, first_name="Grace", last_name="Walker")


@pytest.mark.django_db
class TestPrayerIntentionListCreate:
    def test_create_prayer_intention(self, missionary, owned_contact):
        client = _client(missionary)
        response = client.post(
            LIST_URL,
            {
                "contact": str(owned_contact.id),
                "title": "Healing for surgery",
                "description": "Pray for a successful recovery",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Healing for surgery"
        # Status defaults to active and timestamps are blank on creation.
        assert response.data["status"] == "active"
        assert response.data["answered_at"] is None
        assert response.data["archived_at"] is None
        # Serializer exposes the contact's name and owner name.
        assert response.data["contact_name"] == "Grace Walker"
        assert response.data["owner_name"] == missionary.full_name

        created = PrayerIntention.objects.get(id=response.data["id"])
        assert created.contact_id == owned_contact.id
        assert created.description == "Pray for a successful recovery"

    def test_list_returns_only_owned_intentions(self, missionary, other_missionary, owned_contact):
        mine = PrayerIntention.objects.create(contact=owned_contact, title="Mine")
        their_contact = ContactFactory(owner=other_missionary)
        PrayerIntention.objects.create(contact=their_contact, title="Theirs")

        client = _client(missionary)
        response = client.get(LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        ids = [row["id"] for row in response.data["results"]]
        assert str(mine.id) in ids
        assert len(ids) == 1
        assert response.data["results"][0]["title"] == "Mine"

    def test_list_orders_active_before_answered_before_archived(self, missionary, owned_contact):
        archived = PrayerIntention.objects.create(
            contact=owned_contact, title="Z-archived", status="archived"
        )
        active = PrayerIntention.objects.create(
            contact=owned_contact, title="A-active", status="active"
        )
        answered = PrayerIntention.objects.create(
            contact=owned_contact, title="M-answered", status="answered"
        )

        client = _client(missionary)
        response = client.get(LIST_URL)

        ordered_ids = [row["id"] for row in response.data["results"]]
        assert ordered_ids == [str(active.id), str(answered.id), str(archived.id)]

    def test_list_requires_authentication(self):
        response = APIClient().get(LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_by_title(self, missionary, owned_contact):
        PrayerIntention.objects.create(contact=owned_contact, title="Job interview")
        PrayerIntention.objects.create(contact=owned_contact, title="New house")

        client = _client(missionary)
        response = client.get(LIST_URL, {"search": "interview"})

        titles = [row["title"] for row in response.data["results"]]
        assert titles == ["Job interview"]

    def test_filter_by_status(self, missionary, owned_contact):
        PrayerIntention.objects.create(contact=owned_contact, title="Active one", status="active")
        PrayerIntention.objects.create(
            contact=owned_contact, title="Answered one", status="answered"
        )

        client = _client(missionary)
        response = client.get(LIST_URL, {"status": "answered"})

        titles = [row["title"] for row in response.data["results"]]
        assert titles == ["Answered one"]


@pytest.mark.django_db
class TestPrayerIntentionDetail:
    def test_retrieve_owned_intention(self, missionary, owned_contact):
        intention = PrayerIntention.objects.create(contact=owned_contact, title="Provision")
        client = _client(missionary)
        response = client.get(_detail_url(intention.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Provision"

    def test_retrieve_other_users_intention_returns_404(self, missionary, other_missionary):
        their_contact = ContactFactory(owner=other_missionary)
        intention = PrayerIntention.objects.create(contact=their_contact, title="Hidden")
        client = _client(missionary)
        response = client.get(_detail_url(intention.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_to_answered_sets_answered_at(self, missionary, owned_contact):
        intention = PrayerIntention.objects.create(
            contact=owned_contact, title="Pending", status="active"
        )
        client = _client(missionary)
        response = client.patch(_detail_url(intention.id), {"status": "answered"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "answered"
        assert response.data["answered_at"] is not None
        assert response.data["archived_at"] is None
        intention.refresh_from_db()
        assert intention.answered_at is not None
        assert intention.archived_at is None

    def test_update_to_archived_sets_archived_at_and_clears_answered(
        self, missionary, owned_contact
    ):
        intention = PrayerIntention.objects.create(
            contact=owned_contact,
            title="Was answered",
            status="answered",
            answered_at=timezone.now(),
        )
        client = _client(missionary)
        response = client.patch(_detail_url(intention.id), {"status": "archived"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "archived"
        assert response.data["archived_at"] is not None
        assert response.data["answered_at"] is None
        intention.refresh_from_db()
        assert intention.archived_at is not None
        assert intention.answered_at is None

    def test_update_back_to_active_clears_both_timestamps(self, missionary, owned_contact):
        intention = PrayerIntention.objects.create(
            contact=owned_contact,
            title="Reopen",
            status="archived",
            archived_at=timezone.now(),
        )
        client = _client(missionary)
        response = client.patch(_detail_url(intention.id), {"status": "active"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "active"
        assert response.data["answered_at"] is None
        assert response.data["archived_at"] is None

    def test_update_without_status_change_leaves_timestamps(self, missionary, owned_contact):
        answered_time = timezone.now() - timedelta(days=2)
        intention = PrayerIntention.objects.create(
            contact=owned_contact,
            title="Stay answered",
            status="answered",
            answered_at=answered_time,
        )
        client = _client(missionary)
        response = client.patch(_detail_url(intention.id), {"title": "Renamed"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Renamed"
        intention.refresh_from_db()
        # answered_at must remain because status did not change.
        assert intention.answered_at is not None
        assert intention.status == "answered"

    def test_answered_at_is_read_only_via_payload(self, missionary, owned_contact):
        intention = PrayerIntention.objects.create(
            contact=owned_contact, title="Try inject", status="active"
        )
        client = _client(missionary)
        injected = timezone.now() - timedelta(days=99)
        response = client.patch(
            _detail_url(intention.id),
            {"answered_at": injected.isoformat()},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        intention.refresh_from_db()
        # answered_at is read-only; client value is ignored, status unchanged.
        assert intention.answered_at is None

    def test_delete_owned_intention(self, missionary, owned_contact):
        intention = PrayerIntention.objects.create(contact=owned_contact, title="Remove me")
        client = _client(missionary)
        response = client.delete(_detail_url(intention.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not PrayerIntention.objects.filter(id=intention.id).exists()

    def test_cannot_delete_other_users_intention(self, missionary, other_missionary):
        their_contact = ContactFactory(owner=other_missionary)
        intention = PrayerIntention.objects.create(contact=their_contact, title="Protected")
        client = _client(missionary)
        response = client.delete(_detail_url(intention.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert PrayerIntention.objects.filter(id=intention.id).exists()


@pytest.mark.django_db
class TestMarkPrayedView:
    def test_mark_prayed_sets_last_prayed_at(self, missionary, owned_contact):
        intention = PrayerIntention.objects.create(contact=owned_contact, title="Pray daily")
        assert intention.last_prayed_at is None
        client = _client(missionary)
        response = client.post(_prayed_url(intention.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Marked as prayed."
        intention.refresh_from_db()
        assert intention.last_prayed_at is not None

    def test_mark_prayed_other_user_returns_404(self, missionary, other_missionary):
        their_contact = ContactFactory(owner=other_missionary)
        intention = PrayerIntention.objects.create(contact=their_contact, title="Not yours")
        client = _client(missionary)
        response = client.post(_prayed_url(intention.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        intention.refresh_from_db()
        assert intention.last_prayed_at is None

    def test_mark_prayed_missing_returns_404(self, missionary):
        import uuid

        client = _client(missionary)
        response = client.post(_prayed_url(uuid.uuid4()))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTodaysFocusView:
    def test_empty_focus_when_no_active(self, missionary, owned_contact):
        # Only non-active intentions exist.
        PrayerIntention.objects.create(contact=owned_contact, title="Archived", status="archived")
        client = _client(missionary)
        response = client.get(FOCUS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_focus_caps_at_five(self, missionary, owned_contact):
        for i in range(8):
            PrayerIntention.objects.create(
                contact=owned_contact, title=f"Intention {i}", status="active"
            )
        client = _client(missionary)
        response = client.get(FOCUS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5

    def test_focus_returns_all_when_fewer_than_five(self, missionary, owned_contact):
        created = [
            PrayerIntention.objects.create(contact=owned_contact, title=f"Few {i}", status="active")
            for i in range(3)
        ]
        client = _client(missionary)
        response = client.get(FOCUS_URL)
        assert len(response.data) == 3
        returned_ids = {row["id"] for row in response.data}
        assert returned_ids == {str(c.id) for c in created}

    def test_focus_excludes_non_active_and_other_owners(
        self, missionary, other_missionary, owned_contact
    ):
        active = PrayerIntention.objects.create(
            contact=owned_contact, title="Active focus", status="active"
        )
        PrayerIntention.objects.create(contact=owned_contact, title="Answered", status="answered")
        their_contact = ContactFactory(owner=other_missionary)
        PrayerIntention.objects.create(contact=their_contact, title="Other active", status="active")
        client = _client(missionary)
        response = client.get(FOCUS_URL)
        ids = [row["id"] for row in response.data]
        assert ids == [str(active.id)]

    def test_focus_is_deterministic_for_same_day(self, missionary, owned_contact):
        for i in range(8):
            PrayerIntention.objects.create(contact=owned_contact, title=f"Det {i}", status="active")
        client = _client(missionary)
        first = [row["id"] for row in client.get(FOCUS_URL).data]
        second = [row["id"] for row in client.get(FOCUS_URL).data]
        assert first == second
