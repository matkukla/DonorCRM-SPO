"""
Behavioral coverage tests for apps.contacts.views.

Exercises the sub-resource list views (gifts, recurring gifts, tasks, prayer
intentions, journal events), the emails endpoint, the thank endpoint's
not-found path, the admin/supervisor owner filter, and the
merge/dismiss permission and validation branches. Each test asserts real
DRF status codes, payload values, and owner-scoping so it fails when the
underlying feature breaks.
"""
import uuid
from datetime import date, timedelta

from rest_framework.test import APIClient

import pytest

from apps.contacts.models import DismissedDuplicate
from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.journals.models import (
    Journal,
    JournalContact,
    JournalStageEvent,
    PipelineStage,
    StageEventType,
)
from apps.prayers.models import PrayerIntention
from apps.tasks.tests.factories import TaskFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user():
    return UserFactory(role="missionary")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_user():
    return UserFactory(role="missionary")


@pytest.mark.django_db
class TestContactThankView:
    """POST /api/v1/contacts/{pk}/thank/"""

    def test_thank_marks_contact(self, auth_client, user):
        contact = ContactFactory(owner=user, needs_thank_you=True)
        resp = auth_client.post(f"/api/v1/contacts/{contact.id}/thank/")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Contact marked as thanked."
        contact.refresh_from_db()
        assert contact.needs_thank_you is False
        assert contact.last_thanked_at is not None

    def test_thank_missing_contact_returns_404(self, auth_client):
        resp = auth_client.post(f"/api/v1/contacts/{uuid.uuid4()}/thank/")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Contact not found."

    def test_thank_other_users_contact_returns_404(self, auth_client, other_user):
        """Owner-scoping: cannot thank another user's contact."""
        contact = ContactFactory(owner=other_user, needs_thank_you=True)
        resp = auth_client.post(f"/api/v1/contacts/{contact.id}/thank/")
        assert resp.status_code == 404
        contact.refresh_from_db()
        assert contact.needs_thank_you is True  # unchanged

    def test_thank_merged_contact_returns_404(self, auth_client, user):
        contact = ContactFactory(owner=user, needs_thank_you=True, is_merged=True)
        resp = auth_client.post(f"/api/v1/contacts/{contact.id}/thank/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestContactGiftsView:
    """GET /api/v1/contacts/{pk}/donations/"""

    def test_lists_gifts_newest_first(self, auth_client, user):
        contact = ContactFactory(owner=user)
        old = GiftFactory(
            donor_contact=contact, amount_cents=5000, gift_date=date.today() - timedelta(days=10)
        )
        new = GiftFactory(donor_contact=contact, amount_cents=9000, gift_date=date.today())
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/donations/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Ordered by -gift_date
        assert data[0]["id"] == str(new.id)
        assert data[1]["id"] == str(old.id)

    def test_does_not_list_other_users_gifts(self, auth_client, other_user):
        contact = ContactFactory(owner=other_user)
        GiftFactory(donor_contact=contact, amount_cents=5000)
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/donations/")
        # Owner-scoped queryset returns nothing for a foreign contact
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.django_db
class TestContactRecurringGiftsView:
    """GET /api/v1/contacts/{pk}/pledges/"""

    def test_lists_recurring_gifts(self, auth_client, user):
        contact = ContactFactory(owner=user)
        rg = RecurringGiftFactory(donor_contact=contact, amount_cents=10000)
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/pledges/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(rg.id)
        assert data[0]["amount_cents"] == 10000

    def test_does_not_list_other_users_recurring_gifts(self, auth_client, other_user):
        contact = ContactFactory(owner=other_user)
        RecurringGiftFactory(donor_contact=contact)
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/pledges/")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.django_db
class TestContactTasksView:
    """GET /api/v1/contacts/{pk}/tasks/"""

    def test_lists_tasks_for_contact(self, auth_client, user):
        contact = ContactFactory(owner=user)
        task = TaskFactory(owner=user, contact=contact)
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/tasks/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(task.id)

    def test_does_not_list_other_users_tasks(self, auth_client, other_user):
        contact = ContactFactory(owner=other_user)
        TaskFactory(owner=other_user, contact=contact)
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/tasks/")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.django_db
class TestContactPrayerIntentionsView:
    """GET /api/v1/contacts/{pk}/prayer-intentions/"""

    def test_lists_prayer_intentions(self, auth_client, user):
        contact = ContactFactory(owner=user)
        pi = PrayerIntention.objects.create(contact=contact, title="Healing", description="d")
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/prayer-intentions/")
        assert resp.status_code == 200
        body = resp.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        ids = [r["id"] for r in results]
        assert str(pi.id) in ids

    def test_other_users_prayer_intentions_not_listed(self, auth_client, other_user):
        contact = ContactFactory(owner=other_user)
        PrayerIntention.objects.create(contact=contact, title="Private", description="d")
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/prayer-intentions/")
        assert resp.status_code == 200
        body = resp.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert results == []


@pytest.mark.django_db
class TestContactJournalsViewFallback:
    """GET /api/v1/contacts/{pk}/journals/ — current_stage fallback path."""

    def test_current_stage_defaults_to_contact_when_no_events(self, auth_client, user):
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="J", goal_amount=1000)
        JournalContact.objects.create(journal=journal, contact=contact)
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/journals/")
        assert resp.status_code == 200
        body = resp.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert len(results) == 1
        # No stage events -> fallback to CONTACT, no decision -> None
        assert results[0]["current_stage"] == PipelineStage.CONTACT
        assert results[0]["decision"] is None


@pytest.mark.django_db
class TestContactJournalEventsView:
    """GET /api/v1/contacts/{pk}/journal-events/"""

    def test_lists_journal_events_with_metadata(self, auth_client, user):
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="Campaign", goal_amount=2000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        event = JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.MEET,
            event_type=StageEventType.MEETING_COMPLETED,
            notes="Great chat",
            triggered_by=user,
        )
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/journal-events/")
        assert resp.status_code == 200
        body = resp.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert len(results) == 1
        row = results[0]
        assert row["id"] == str(event.id)
        assert row["event_type"] == StageEventType.MEETING_COMPLETED
        assert row["stage"] == PipelineStage.MEET
        assert row["notes"] == "Great chat"
        assert row["journal_name"] == "Campaign"
        assert row["journal_id"] == str(journal.id)
        assert row["journal_contact_id"] == str(jc.id)

    def test_journal_events_paginated(self, auth_client, user):
        """More than one page of events returns a paginated envelope."""
        contact = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="Big", goal_amount=2000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        # StandardPagination page_size = 25; create 30 events.
        for _ in range(30):
            JournalStageEvent.objects.create(
                journal_contact=jc,
                stage=PipelineStage.CONTACT,
                event_type=StageEventType.CALL_LOGGED,
                triggered_by=user,
            )
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/journal-events/")
        assert resp.status_code == 200
        body = resp.json()
        # Paginated envelope present
        assert body["count"] == 30
        assert len(body["results"]) == 25
        assert body["next"] is not None

    def test_other_users_journal_events_not_visible(self, auth_client, other_user):
        contact = ContactFactory(owner=other_user)
        journal = Journal.objects.create(owner=other_user, name="Private", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        JournalStageEvent.objects.create(
            journal_contact=jc,
            stage=PipelineStage.CONTACT,
            event_type=StageEventType.CALL_LOGGED,
            triggered_by=other_user,
        )
        resp = auth_client.get(f"/api/v1/contacts/{contact.id}/journal-events/")
        assert resp.status_code == 200
        body = resp.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert results == []


@pytest.mark.django_db
class TestContactEmailsView:
    """GET /api/v1/contacts/emails/"""

    def test_returns_emails_for_owned_contacts(self, auth_client, user):
        ContactFactory(owner=user, email="alice@example.com")
        ContactFactory(owner=user, email="bob@example.com")
        ContactFactory(owner=user, email="")  # excluded (blank)
        resp = auth_client.get("/api/v1/contacts/emails/")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["emails"]) == {"alice@example.com", "bob@example.com"}
        assert data["count"] == 2

    def test_excludes_merged_and_other_users(self, auth_client, user, other_user):
        ContactFactory(owner=user, email="keep@example.com")
        ContactFactory(owner=user, email="gone@example.com", is_merged=True)
        ContactFactory(owner=other_user, email="foreign@example.com")
        resp = auth_client.get("/api/v1/contacts/emails/")
        assert resp.status_code == 200
        emails = resp.json()["emails"]
        assert emails == ["keep@example.com"]

    def test_status_filter_applied(self, auth_client, user):
        from apps.contacts.models import ContactStatus

        ContactFactory(owner=user, email="donor@example.com", status=ContactStatus.DONOR)
        ContactFactory(owner=user, email="prospect@example.com", status=ContactStatus.PROSPECT)
        resp = auth_client.get("/api/v1/contacts/emails/?status=donor")
        assert resp.status_code == 200
        assert resp.json()["emails"] == ["donor@example.com"]

    def test_search_full_email_match(self, auth_client, user):
        ContactFactory(owner=user, first_name="Zoe", last_name="Zephyr", email="zoe@example.com")
        ContactFactory(owner=user, first_name="Mike", last_name="Other", email="mike@example.com")
        # Full-email blind-index match
        resp = auth_client.get("/api/v1/contacts/emails/?search=zoe@example.com")
        assert resp.status_code == 200
        assert resp.json()["emails"] == ["zoe@example.com"]

    def test_search_by_first_name_substring(self, auth_client, user):
        ContactFactory(owner=user, first_name="Zoe", last_name="Zephyr", email="zoe@example.com")
        ContactFactory(owner=user, first_name="Mike", last_name="Other", email="mike@example.com")
        resp = auth_client.get("/api/v1/contacts/emails/?search=Zoe")
        assert resp.status_code == 200
        assert resp.json()["emails"] == ["zoe@example.com"]

    def test_owner_filter_for_coach(self):
        """A coach can scope emails to a specific coached missionary via ?owner=."""
        coach = UserFactory(role="coach")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        coach.coached_users.add(m1, m2)
        ContactFactory(owner=m1, email="m1@example.com")
        ContactFactory(owner=m2, email="m2@example.com")
        client = APIClient()
        client.force_authenticate(user=coach)
        resp = client.get(f"/api/v1/contacts/emails/?owner={m1.id}")
        assert resp.status_code == 200
        # owner filter narrows to m1's contacts only
        assert resp.json()["emails"] == ["m1@example.com"]


@pytest.mark.django_db
class TestContactListOwnerFilter:
    """GET /api/v1/contacts/?owner=... — admin/supervisor scoping branch."""

    def test_admin_owner_filter_via_view_as(self):
        """Admin with View As targeting a missionary, filtered by that owner."""
        admin = UserFactory(role="admin")
        target = UserFactory(role="missionary")
        c1 = ContactFactory(owner=target, first_name="Target", last_name="One")

        client = APIClient()
        client.force_authenticate(user=admin)
        # View As makes the target's data visible; owner filter narrows to them.
        resp = client.get(
            f"/api/v1/contacts/?owner={target.id}",
            HTTP_X_VIEW_AS_USER_ID=str(target.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        ids = [r["id"] for r in results]
        assert str(c1.id) in ids

    def test_missionary_owner_filter_ignored(self, auth_client, user, other_user):
        """A missionary passing ?owner=<other> still only sees own contacts.

        The owner filter branch only runs for admin/supervisor/coach roles,
        so the param is silently ignored for missionaries (security).
        """
        mine = ContactFactory(owner=user, first_name="Mine")
        ContactFactory(owner=other_user, first_name="Theirs")
        resp = auth_client.get(f"/api/v1/contacts/?owner={other_user.id}")
        assert resp.status_code == 200
        body = resp.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        ids = [r["id"] for r in results]
        # Only own contact; foreign owner filter cannot leak others' data
        assert str(mine.id) in ids
        assert len(ids) == 1


@pytest.mark.django_db
class TestMergeContactsViewBranches:
    """POST /api/v1/contacts/duplicates/merge/ permission + validation branches."""

    def test_merge_loser_not_visible_returns_404(self):
        """A missionary cannot merge in a loser owned by another user (404)."""
        user = UserFactory(role="missionary")
        other = UserFactory(role="missionary")
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=other)
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.post(
            "/api/v1/contacts/duplicates/merge/",
            {"survivor_id": str(survivor.id), "loser_id": str(loser.id)},
            format="json",
        )
        # loser not visible to this missionary -> 404
        assert resp.status_code == 404

    def test_merge_with_self_returns_400(self, auth_client, user):
        """Merging a contact with itself raises ValueError -> 400."""
        contact = ContactFactory(owner=user)
        resp = auth_client.post(
            "/api/v1/contacts/duplicates/merge/",
            {"survivor_id": str(contact.id), "loser_id": str(contact.id)},
            format="json",
        )
        assert resp.status_code == 400
        assert "itself" in resp.json()["detail"].lower()

    def test_merge_already_merged_returns_400(self, auth_client, user):
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user, is_merged=True)
        resp = auth_client.post(
            "/api/v1/contacts/duplicates/merge/",
            {"survivor_id": str(survivor.id), "loser_id": str(loser.id)},
            format="json",
        )
        # is_merged loser is excluded from list scoping -> not found -> 404
        # (loser query uses owner_id__in=visible without is_merged filter,
        # so it IS found, then service raises ValueError -> 400)
        assert resp.status_code == 400
        assert "already been merged" in resp.json()["detail"]

    def test_admin_merge_success_returns_survivor(self):
        """An admin merging two of their own contacts gets the survivor payload."""
        admin = UserFactory(role="admin")
        survivor = ContactFactory(owner=admin, first_name="Alice", last_name="Smith")
        loser = ContactFactory(owner=admin, first_name="Alice", last_name="Smithe")
        client = APIClient()
        client.force_authenticate(user=admin)
        resp = client.post(
            "/api/v1/contacts/duplicates/merge/",
            {"survivor_id": str(survivor.id), "loser_id": str(loser.id)},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(survivor.id)
        loser.refresh_from_db()
        assert loser.is_merged is True


@pytest.mark.django_db
class TestDismissDuplicateViewBranches:
    """POST /api/v1/contacts/duplicates/dismiss/ permission + validation branches."""

    def test_dismiss_missing_contact_returns_404(self, auth_client, user):
        c1 = ContactFactory(owner=user)
        resp = auth_client.post(
            "/api/v1/contacts/duplicates/dismiss/",
            {"contact_a_id": str(c1.id), "contact_b_id": str(uuid.uuid4())},
            format="json",
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Contact not found."

    def test_dismiss_other_users_contact_returns_404(self, auth_client, user, other_user):
        mine = ContactFactory(owner=user)
        theirs = ContactFactory(owner=other_user)
        resp = auth_client.post(
            "/api/v1/contacts/duplicates/dismiss/",
            {"contact_a_id": str(mine.id), "contact_b_id": str(theirs.id)},
            format="json",
        )
        assert resp.status_code == 404
        assert DismissedDuplicate.objects.count() == 0

    def test_dismiss_is_idempotent(self, auth_client, user):
        c1 = ContactFactory(owner=user)
        c2 = ContactFactory(owner=user)
        payload = {"contact_a_id": str(c1.id), "contact_b_id": str(c2.id)}
        r1 = auth_client.post("/api/v1/contacts/duplicates/dismiss/", payload, format="json")
        r2 = auth_client.post("/api/v1/contacts/duplicates/dismiss/", payload, format="json")
        assert r1.status_code == 201
        assert r2.status_code == 201
        # get_or_create canonicalizes the pair -> only one row
        assert DismissedDuplicate.objects.count() == 1
