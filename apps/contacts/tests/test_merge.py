"""
Tests for contact merge functionality.
All tests are SQLite-safe (no pg_trgm usage).
"""
from datetime import date, timedelta

from django.utils import timezone

import pytest

from apps.contacts.models import Contact, ContactMergeLog
from apps.contacts.tests.factories import ContactFactory
from apps.events.tests.factories import EventFactory
from apps.gifts.tests.factories import GiftFactory, RecurringGiftFactory
from apps.groups.tests.factories import GroupFactory
from apps.tasks.tests.factories import TaskFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestMergeContacts:
    """Test merge_contacts service function."""

    def test_merge_reassigns_gifts(self):
        """After merge, gifts from loser belong to survivor."""
        from apps.contacts.services import merge_contacts
        from apps.gifts.models import Gift

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        gift = GiftFactory(donor_contact=loser)

        merge_contacts(survivor.id, loser.id, merged_by=user)

        gift.refresh_from_db()
        assert gift.donor_contact_id == survivor.id
        assert Gift.objects.filter(donor_contact=survivor).count() == 1

    def test_merge_reassigns_recurring_gifts(self):
        """After merge, recurring gifts from loser belong to survivor."""
        from apps.contacts.services import merge_contacts
        from apps.gifts.models import RecurringGift

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        rg = RecurringGiftFactory(donor_contact=loser)

        merge_contacts(survivor.id, loser.id, merged_by=user)

        rg.refresh_from_db()
        assert rg.donor_contact_id == survivor.id
        assert RecurringGift.objects.filter(donor_contact=survivor).count() == 1

    def test_merge_reassigns_tasks(self):
        """After merge, tasks from loser belong to survivor."""
        from apps.contacts.services import merge_contacts
        from apps.tasks.models import Task

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        task = TaskFactory(owner=user, contact=loser)

        merge_contacts(survivor.id, loser.id, merged_by=user)

        task.refresh_from_db()
        assert task.contact_id == survivor.id

    def test_merge_reassigns_prayer_intentions(self):
        """After merge, prayer intentions from loser belong to survivor."""
        from apps.contacts.services import merge_contacts
        from apps.prayers.models import PrayerIntention

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        pi = PrayerIntention.objects.create(contact=loser, title="Test prayer", description="Desc")

        merge_contacts(survivor.id, loser.id, merged_by=user)

        pi.refresh_from_db()
        assert pi.contact_id == survivor.id

    def test_merge_reassigns_events(self):
        """After merge, events linked to loser contact are reassigned to survivor."""
        from apps.contacts.services import merge_contacts
        from apps.events.models import Event

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        event = EventFactory(user=user, contact=loser)

        merge_contacts(survivor.id, loser.id, merged_by=user)

        event.refresh_from_db()
        assert event.contact_id == survivor.id

    def test_merge_journal_contact_no_conflict(self):
        """Loser's JournalContact not shared with survivor gets reassigned."""
        from apps.contacts.services import merge_contacts
        from apps.journals.models import Journal, JournalContact

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="Test Journal", goal_amount=1000)
        jc = JournalContact.objects.create(journal=journal, contact=loser)

        merge_contacts(survivor.id, loser.id, merged_by=user)

        jc.refresh_from_db()
        assert jc.contact_id == survivor.id

    def test_merge_journal_contact_with_conflict(self):
        """Both contacts in same journal: loser JC events moved to survivor JC, loser JC deleted."""
        from apps.contacts.services import merge_contacts
        from apps.journals.models import (
            Journal,
            JournalContact,
            JournalStageEvent,
            PipelineStage,
            StageEventType,
        )

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        journal = Journal.objects.create(owner=user, name="Test Journal", goal_amount=1000)
        survivor_jc = JournalContact.objects.create(journal=journal, contact=survivor)
        loser_jc = JournalContact.objects.create(journal=journal, contact=loser)

        # Create stage event on loser JC
        event = JournalStageEvent.objects.create(
            journal_contact=loser_jc,
            stage=PipelineStage.CONTACT,
            event_type=StageEventType.CALL_LOGGED,
            triggered_by=user,
        )

        merge_contacts(survivor.id, loser.id, merged_by=user)

        # loser JC should be deleted
        assert not JournalContact.objects.filter(pk=loser_jc.pk).exists()
        # event should now belong to survivor JC
        event.refresh_from_db()
        assert event.journal_contact_id == survivor_jc.id

    def test_merge_union_groups(self):
        """Loser's groups are union-merged into survivor's groups."""
        from apps.contacts.services import merge_contacts

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        group_a = GroupFactory(owner=user)
        group_b = GroupFactory(owner=user)
        group_shared = GroupFactory(owner=user)

        survivor.groups.add(group_a, group_shared)
        loser.groups.add(group_b, group_shared)

        merge_contacts(survivor.id, loser.id, merged_by=user)

        survivor.refresh_from_db()
        group_ids = set(survivor.groups.values_list("id", flat=True))
        assert group_a.id in group_ids
        assert group_b.id in group_ids
        assert group_shared.id in group_ids
        assert len(group_ids) == 3

    def test_merge_soft_deletes_loser(self):
        """Loser is marked as merged with merged_into pointing to survivor."""
        from apps.contacts.services import merge_contacts

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)

        merge_contacts(survivor.id, loser.id, merged_by=user)

        loser.refresh_from_db()
        assert loser.is_merged is True
        assert loser.merged_into_id == survivor.id

    def test_merge_creates_audit_log(self):
        """A ContactMergeLog record is created with correct metadata."""
        from apps.contacts.services import merge_contacts

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        loser_id = loser.id

        merge_contacts(survivor.id, loser.id, merged_by=user)

        assert ContactMergeLog.objects.count() == 1
        log = ContactMergeLog.objects.first()
        assert log.survivor_id == survivor.id
        assert log.loser_id == loser_id
        assert log.merged_by_id == user.id
        assert "gifts" in log.records_migrated

    def test_merge_auto_fills_blanks(self):
        """Survivor's blank fields get filled from loser's non-empty values."""
        from apps.contacts.services import merge_contacts

        user = UserFactory()
        survivor = ContactFactory(owner=user, email="survivor@example.com", phone="")
        loser = ContactFactory(owner=user, email="loser@example.com", phone="555-1234")

        merge_contacts(survivor.id, loser.id, merged_by=user)

        survivor.refresh_from_db()
        assert survivor.phone == "555-1234"  # Auto-filled from loser
        assert survivor.email == "survivor@example.com"  # Kept (non-blank)

    def test_merge_does_not_overwrite_survivor_fields(self):
        """Survivor's populated fields are never overwritten by loser's values."""
        from apps.contacts.services import merge_contacts

        user = UserFactory()
        survivor = ContactFactory(owner=user, first_name="Alice", email="alice@example.com")
        loser = ContactFactory(owner=user, first_name="Bob", email="bob@example.com")

        merge_contacts(survivor.id, loser.id, merged_by=user)

        survivor.refresh_from_db()
        assert survivor.first_name == "Alice"  # Not overwritten
        assert survivor.email == "alice@example.com"  # Not overwritten

    def test_merge_recalculates_stats(self):
        """Survivor's giving stats include transferred gifts after merge."""
        from apps.contacts.services import merge_contacts

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user)
        GiftFactory(donor_contact=loser, amount_cents=10000, gift_date=date.today())

        merge_contacts(survivor.id, loser.id, merged_by=user)

        survivor.refresh_from_db()
        assert survivor.gift_count == 1
        assert survivor.total_given > 0

    def test_merge_already_merged_raises(self):
        """Merging an already-merged contact raises ValueError."""
        from apps.contacts.services import merge_contacts

        user = UserFactory()
        survivor = ContactFactory(owner=user)
        loser = ContactFactory(owner=user, is_merged=True)

        with pytest.raises(ValueError, match="already been merged"):
            merge_contacts(survivor.id, loser.id, merged_by=user)
