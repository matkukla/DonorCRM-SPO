"""Tests for the 0011 follow-up latch backfill/heal migration data function.

Exercises the pure data-migration callable ``backfill_and_heal`` against the live
model registry. Focus: the one-to-one Decision→Task pairing that issue #186 fixes —
a contact with multiple pending follow-up Tasks must not have every latched Decision
point at the same newest Task.
"""

import importlib
from datetime import timedelta

from django.apps import apps as django_apps
from django.utils import timezone

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.journals.models import Decision, Journal, JournalContact
from apps.tasks.models import Task, TaskStatus, TaskType
from apps.users.tests.factories import UserFactory

# Migration module names start with a digit, so they cannot be imported with a normal
# ``import`` statement. Load the callable via importlib instead.
_migration = importlib.import_module(
    "apps.journals.migrations.0011_backfill_and_heal_follow_up_latch"
)
backfill_and_heal = _migration.backfill_and_heal
FOLLOW_UP_TITLE = _migration.FOLLOW_UP_TITLE


def _latched_decision(owner, contact, created_offset_days):
    """A Decision with follow_up_created_at set but follow_up_task NULL (pre-FK state).

    ``created_offset_days`` ages the Decision so ordering is deterministic.
    """
    journal = Journal.objects.create(owner=owner, name="Campaign", goal_amount="50000.00")
    jc = JournalContact.objects.create(journal=journal, contact=contact)
    decision = Decision.objects.create(journal_contact=jc, amount="100.00")
    aged = timezone.now() - timedelta(days=created_offset_days)
    Decision.objects.filter(pk=decision.pk).update(
        created_at=aged, follow_up_created_at=aged, follow_up_task=None
    )
    decision.refresh_from_db()
    return decision


def _pending_followup_task(owner, contact, created_offset_days):
    """A live, unlatched follow-up Task (no FK back to a Decision), aged for ordering."""
    task = Task.objects.create(
        owner=owner,
        contact=contact,
        title=FOLLOW_UP_TITLE,
        task_type=TaskType.FOLLOW_UP,
        status=TaskStatus.PENDING,
        auto_generated=True,
        due_date=timezone.now().date() + timedelta(days=7),
    )
    aged = timezone.now() - timedelta(days=created_offset_days)
    Task.objects.filter(pk=task.pk).update(created_at=aged)
    task.refresh_from_db()
    return task


@pytest.mark.django_db
class TestBackfillOneToOnePairing:
    def test_two_pending_followups_pair_distinct_tasks(self):
        """The #186 bug: two latched Decisions on one contact must claim two Tasks."""
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)

        # Two latched Decisions and two separate pending follow-up Tasks for the contact.
        older_decision = _latched_decision(owner, contact, created_offset_days=30)
        newer_decision = _latched_decision(owner, contact, created_offset_days=10)
        older_task = _pending_followup_task(owner, contact, created_offset_days=28)
        newer_task = _pending_followup_task(owner, contact, created_offset_days=8)

        backfill_and_heal(django_apps, None)

        older_decision.refresh_from_db()
        newer_decision.refresh_from_db()

        # Each Decision points at a distinct Task (no double-claim of the newest).
        assert older_decision.follow_up_task_id is not None
        assert newer_decision.follow_up_task_id is not None
        assert older_decision.follow_up_task_id != newer_decision.follow_up_task_id
        assert {older_decision.follow_up_task_id, newer_decision.follow_up_task_id} == {
            older_task.id,
            newer_task.id,
        }
        # Latches remain set (both had a live Task to claim).
        assert older_decision.follow_up_created_at is not None
        assert newer_decision.follow_up_created_at is not None

    def test_oldest_decision_claims_oldest_task(self):
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)

        older_decision = _latched_decision(owner, contact, created_offset_days=30)
        newer_decision = _latched_decision(owner, contact, created_offset_days=10)
        older_task = _pending_followup_task(owner, contact, created_offset_days=28)
        newer_task = _pending_followup_task(owner, contact, created_offset_days=8)

        backfill_and_heal(django_apps, None)

        older_decision.refresh_from_db()
        newer_decision.refresh_from_db()
        assert older_decision.follow_up_task_id == older_task.id
        assert newer_decision.follow_up_task_id == newer_task.id

    def test_more_decisions_than_tasks_heals_the_extra(self):
        """Two latched Decisions but only one live Task: one backfills, one heals."""
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)

        older_decision = _latched_decision(owner, contact, created_offset_days=30)
        newer_decision = _latched_decision(owner, contact, created_offset_days=10)
        the_task = _pending_followup_task(owner, contact, created_offset_days=28)

        backfill_and_heal(django_apps, None)

        older_decision.refresh_from_db()
        newer_decision.refresh_from_db()

        # Oldest Decision claims the one Task; the extra is healed (latch cleared).
        assert older_decision.follow_up_task_id == the_task.id
        assert older_decision.follow_up_created_at is not None
        assert newer_decision.follow_up_task_id is None
        assert newer_decision.follow_up_created_at is None


@pytest.mark.django_db
class TestBackfillSingleAndHeal:
    def test_single_latched_decision_backfills(self):
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)
        decision = _latched_decision(owner, contact, created_offset_days=10)
        task = _pending_followup_task(owner, contact, created_offset_days=8)

        backfill_and_heal(django_apps, None)

        decision.refresh_from_db()
        assert decision.follow_up_task_id == task.id
        assert decision.follow_up_created_at is not None

    def test_latched_decision_with_no_task_heals(self):
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)
        decision = _latched_decision(owner, contact, created_offset_days=10)

        backfill_and_heal(django_apps, None)

        decision.refresh_from_db()
        assert decision.follow_up_task_id is None
        assert decision.follow_up_created_at is None

    def test_completed_and_cancelled_tasks_are_not_claimed(self):
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)
        decision = _latched_decision(owner, contact, created_offset_days=10)
        done = _pending_followup_task(owner, contact, created_offset_days=8)
        Task.objects.filter(pk=done.pk).update(status=TaskStatus.COMPLETED)

        backfill_and_heal(django_apps, None)

        decision.refresh_from_db()
        # No live Task → healed, not pointed at the completed one.
        assert decision.follow_up_task_id is None
        assert decision.follow_up_created_at is None

    def test_tasks_of_other_contacts_are_not_claimed(self):
        owner = UserFactory(role="missionary")
        contact_a = ContactFactory(owner=owner)
        contact_b = ContactFactory(owner=owner)
        decision_a = _latched_decision(owner, contact_a, created_offset_days=10)
        task_b = _pending_followup_task(owner, contact_b, created_offset_days=8)

        backfill_and_heal(django_apps, None)

        decision_a.refresh_from_db()
        # contact_a has no Task of its own → healed; task_b stays unclaimed.
        assert decision_a.follow_up_task_id is None
        assert decision_a.follow_up_created_at is None
        assert not Decision.objects.filter(follow_up_task=task_b).exists()

    def test_unlatched_decision_is_untouched(self):
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)
        journal = Journal.objects.create(owner=owner, name="Campaign", goal_amount="50000.00")
        jc = JournalContact.objects.create(journal=journal, contact=contact)
        decision = Decision.objects.create(journal_contact=jc, amount="100.00")
        # A live Task exists, but the Decision is not latched → must stay unclaimed.
        _pending_followup_task(owner, contact, created_offset_days=8)

        backfill_and_heal(django_apps, None)

        decision.refresh_from_db()
        assert decision.follow_up_task_id is None
        assert decision.follow_up_created_at is None
