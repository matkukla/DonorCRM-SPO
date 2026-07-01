"""
Tests for the pledge follow-up sweep (issue #99).

Covers the three acceptance paths — fulfillment rule, the unfulfilled-pledge path,
and idempotency — plus timing, eligibility, and multi-pledge edge cases. Also exercises
the management command and the Celery task wrapper that drive the same sweep.
"""

from datetime import timedelta

from django.utils import timezone

import pytest

from apps.contacts.models import Contact
from apps.contacts.tests.factories import ContactFactory
from apps.gifts.tests.factories import (
    CancelledRecurringGiftFactory,
    GiftFactory,
    RecurringGiftFactory,
)
from apps.journals.models import Decision, DecisionStatus, Journal, JournalContact
from apps.journals.pledge_followup import (
    is_pledge_fulfilled,
    release_followup,
    run_pledge_followup_sweep,
)
from apps.tasks.models import Task, TaskStatus, TaskType
from apps.users.tests.factories import UserFactory


def _make_pledge(owner=None, amount="100.00", status=DecisionStatus.ACTIVE, age_days=10):
    """Create an active pledge (Decision) whose created_at is ``age_days`` old.

    Returns the (contact, decision) pair. created_at is auto_now_add, so it is forced
    via an UPDATE after creation to simulate an aged pledge.
    """
    owner = owner or UserFactory(role="missionary")
    contact = ContactFactory(owner=owner)
    journal = Journal.objects.create(owner=owner, name="Campaign", goal_amount="50000.00")
    jc = JournalContact.objects.create(journal=journal, contact=contact)
    decision = Decision.objects.create(journal_contact=jc, amount=amount, status=status)
    aged = timezone.now() - timedelta(days=age_days)
    Decision.objects.filter(pk=decision.pk).update(created_at=aged)
    decision.refresh_from_db()
    return contact, decision


@pytest.mark.django_db
class TestFulfillmentRule:
    """is_pledge_fulfilled and the no-follow-up paths."""

    def test_qualifying_gift_fulfills(self):
        contact, decision = _make_pledge(amount="100.00")
        GiftFactory(donor_contact=contact, amount_cents=10000, gift_date=timezone.now().date())
        assert is_pledge_fulfilled(decision) is True
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 0

    def test_larger_gift_fulfills(self):
        contact, decision = _make_pledge(amount="100.00")
        GiftFactory(donor_contact=contact, amount_cents=15000, gift_date=timezone.now().date())
        assert run_pledge_followup_sweep() == 0

    def test_active_recurring_gift_fulfills(self):
        contact, decision = _make_pledge(amount="100.00")
        RecurringGiftFactory(donor_contact=contact)
        assert is_pledge_fulfilled(decision) is True
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 0

    def test_cancelled_recurring_gift_does_not_fulfill(self):
        contact, decision = _make_pledge(amount="100.00")
        CancelledRecurringGiftFactory(donor_contact=contact)
        assert is_pledge_fulfilled(decision) is False
        assert run_pledge_followup_sweep() == 1

    def test_partial_gift_does_not_fulfill(self):
        contact, decision = _make_pledge(amount="100.00")
        # Two $50 gifts against a $100 pledge — neither individually meets the amount.
        GiftFactory(donor_contact=contact, amount_cents=5000, gift_date=timezone.now().date())
        GiftFactory(donor_contact=contact, amount_cents=5000, gift_date=timezone.now().date())
        assert is_pledge_fulfilled(decision) is False
        assert run_pledge_followup_sweep() == 1

    def test_exact_cents_pledge_is_fulfilled_by_exact_gift(self):
        """An amount with cents (e.g. $100.07) must convert to exactly 10007 cents.

        Guards the Decimal->cents conversion against float rounding error: a gift
        of exactly the pledged cents must fulfill the pledge.
        """
        contact, decision = _make_pledge(amount="100.07")
        GiftFactory(donor_contact=contact, amount_cents=10007, gift_date=timezone.now().date())
        assert is_pledge_fulfilled(decision) is True

    def test_gift_before_pledge_date_does_not_fulfill(self):
        contact, decision = _make_pledge(amount="100.00", age_days=10)
        pledge_date = decision.created_at.date()
        GiftFactory(
            donor_contact=contact,
            amount_cents=10000,
            gift_date=pledge_date - timedelta(days=1),
        )
        assert is_pledge_fulfilled(decision) is False
        assert run_pledge_followup_sweep() == 1


@pytest.mark.django_db
class TestUnfulfilledPath:
    """The follow-up Task is created correctly when a pledge is unfulfilled."""

    def test_creates_one_followup_with_expected_fields(self):
        owner = UserFactory(role="missionary")
        contact, decision = _make_pledge(owner=owner, amount="100.00")

        assert run_pledge_followup_sweep() == 1

        task = Task.objects.get()
        assert task.title == "Donation still not received — follow up"
        assert task.task_type == TaskType.FOLLOW_UP
        assert task.status == TaskStatus.PENDING
        assert task.auto_generated is True
        assert task.owner == owner
        assert task.contact == contact
        assert task.due_date == timezone.now().date() + timedelta(days=3)

        decision.refresh_from_db()
        assert decision.follow_up_created_at is not None
        assert decision.follow_up_task == task


@pytest.mark.django_db
class TestFollowUpLatchReset:
    """Deleting the follow-up Task re-arms the sweep; other actions do not.

    See docs/adr/0010-follow-up-latch-resets-on-task-delete.md.
    """

    def test_deleting_task_clears_latch_and_fk(self):
        _contact, decision = _make_pledge(amount="100.00")
        assert run_pledge_followup_sweep() == 1
        task = Task.objects.get()

        task.delete()

        decision.refresh_from_db()
        assert decision.follow_up_created_at is None
        assert decision.follow_up_task is None

    def test_deleting_task_re_arms_sweep_when_still_unfulfilled(self):
        _contact, decision = _make_pledge(amount="100.00")
        assert run_pledge_followup_sweep() == 1
        Task.objects.get().delete()

        # Pledge is still unfulfilled, so a fresh follow-up is created.
        assert run_pledge_followup_sweep() == 1
        assert Task.objects.count() == 1
        decision.refresh_from_db()
        assert decision.follow_up_created_at is not None

    def test_completing_task_does_not_re_arm(self):
        owner = UserFactory(role="missionary")
        _contact, decision = _make_pledge(owner=owner, amount="100.00")
        assert run_pledge_followup_sweep() == 1
        task = Task.objects.get()

        task.mark_complete(owner)

        # Completed Task still exists → latch stays set → no duplicate.
        decision.refresh_from_db()
        assert decision.follow_up_created_at is not None
        assert decision.follow_up_task == task
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 1

    def test_reopening_task_does_not_duplicate(self):
        owner = UserFactory(role="missionary")
        _contact, decision = _make_pledge(owner=owner, amount="100.00")
        assert run_pledge_followup_sweep() == 1
        task = Task.objects.get()
        task.mark_complete(owner)
        task.mark_incomplete()

        # A reopened Task is an open Task — the latch correctly suppresses a duplicate.
        decision.refresh_from_db()
        assert decision.follow_up_created_at is not None
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 1

    def test_deleting_non_followup_task_is_noop(self):
        owner = UserFactory(role="missionary")
        _contact, decision = _make_pledge(owner=owner, amount="100.00")
        assert run_pledge_followup_sweep() == 1
        followup = Task.objects.get()

        other = Task.objects.create(
            owner=owner,
            title="Call the donor",
            task_type=TaskType.CALL,
            status=TaskStatus.PENDING,
            due_date=timezone.now().date(),
        )
        assert release_followup(other) is False
        other.delete()

        # The follow-up latch is untouched by an unrelated Task's deletion.
        decision.refresh_from_db()
        assert decision.follow_up_created_at is not None
        assert decision.follow_up_task == followup


@pytest.mark.django_db
class TestDecisionDeleteCleansUpFollowUp:
    """Deleting the Decision (the inverse of deleting its Task) must not orphan the
    follow-up Task. See issue #183 and docs/adr/0010.

    ADR 0010 handles Task deletion re-arming the sweep. This covers the mirror case:
    when the Decision that owns the follow-up Task is destroyed (contact merge or a
    JournalContact cascade), the auto-generated follow-up Task would otherwise be left
    open forever, disconnected from any pledge.
    """

    def test_deleting_decision_deletes_its_followup_task(self):
        _contact, decision = _make_pledge(amount="100.00")
        assert run_pledge_followup_sweep() == 1
        task = Task.objects.get()

        decision.delete()

        assert not Task.objects.filter(pk=task.pk).exists()

    def test_deleting_decision_without_followup_is_noop(self):
        """A Decision that never armed a follow-up leaves unrelated Tasks alone."""
        owner = UserFactory(role="missionary")
        contact, decision = _make_pledge(owner=owner, amount="100.00")
        other = Task.objects.create(
            owner=owner,
            contact=contact,
            title="Call the donor",
            task_type=TaskType.CALL,
            status=TaskStatus.PENDING,
            due_date=timezone.now().date(),
        )

        decision.delete()

        assert Task.objects.filter(pk=other.pk).exists()

    def test_cascading_journalcontact_delete_deletes_followup_task(self):
        """Deleting a JournalContact cascades to its Decision, which must clean up the
        orphaned follow-up Task (reachable via JournalContactDestroyView)."""
        _contact, decision = _make_pledge(amount="100.00")
        assert run_pledge_followup_sweep() == 1
        task = Task.objects.get()
        jc = decision.journal_contact

        jc.delete()

        assert not Decision.objects.filter(pk=decision.pk).exists()
        assert not Task.objects.filter(pk=task.pk).exists()

    def test_merge_conflict_deletes_losers_followup_task(self):
        """When a contact merge hard-deletes the loser's conflicting Decision, its
        follow-up Task must not be orphaned."""
        from apps.contacts.services import merge_contacts

        owner = UserFactory(role="missionary")
        journal = Journal.objects.create(owner=owner, name="Campaign", goal_amount="50000.00")

        survivor = ContactFactory(owner=owner)
        loser = ContactFactory(owner=owner)

        # Both contacts share the journal; each has a Decision -> merge is a conflict
        # that hard-deletes the loser's Decision at services.py.
        survivor_jc = JournalContact.objects.create(journal=journal, contact=survivor)
        loser_jc = JournalContact.objects.create(journal=journal, contact=loser)
        Decision.objects.create(journal_contact=survivor_jc, amount="100.00")
        loser_decision = Decision.objects.create(
            journal_contact=loser_jc, amount="100.00", status=DecisionStatus.ACTIVE
        )
        aged = timezone.now() - timedelta(days=10)
        Decision.objects.filter(pk=loser_decision.pk).update(created_at=aged)

        # Arm a follow-up on the loser's pledge, then merge.
        assert run_pledge_followup_sweep() == 1
        followup = Task.objects.get(auto_generated=True)

        merge_contacts(survivor.id, loser.id, merged_by=owner)

        assert not Decision.objects.filter(pk=loser_decision.pk).exists()
        assert not Task.objects.filter(pk=followup.pk).exists()


@pytest.mark.django_db
class TestBackfillAndHealMigration:
    """The 0011 data migration heals orphaned latches without duplicating live ones.

    Exercises the migration's backfill_and_heal function directly against the current
    model registry (the fields it touches are unchanged from the historical state).
    See docs/adr/0010-follow-up-latch-resets-on-task-delete.md.
    """

    @staticmethod
    def _run_migration():
        import importlib

        from django.apps import apps as global_apps

        mod = importlib.import_module(
            "apps.journals.migrations.0011_backfill_and_heal_follow_up_latch"
        )
        mod.backfill_and_heal(global_apps, None)

    def _latch(self, decision, when=None, task=None):
        """Force the pre-migration latch state directly (bypassing the sweep)."""
        Decision.objects.filter(pk=decision.pk).update(
            follow_up_created_at=when or timezone.now(),
            follow_up_task=task,
        )
        decision.refresh_from_db()

    def test_true_orphan_is_healed(self):
        # Latch set, Task already deleted (no FK) -> the bug. Migration clears it.
        _contact, decision = _make_pledge(amount="100.00")
        self._latch(decision, task=None)

        self._run_migration()

        decision.refresh_from_db()
        assert decision.follow_up_created_at is None
        assert decision.follow_up_task is None

    def test_surviving_task_is_backfilled_not_healed(self):
        # Latch set, follow-up Task still exists but FK not yet populated (pre-0010
        # data). Migration must backfill the FK and KEEP the latch.
        owner = UserFactory(role="missionary")
        contact, decision = _make_pledge(owner=owner, amount="100.00")
        task = Task.objects.create(
            owner=owner,
            contact=contact,
            title="Donation still not received — follow up",
            task_type=TaskType.FOLLOW_UP,
            status=TaskStatus.PENDING,
            due_date=timezone.now().date(),
        )
        self._latch(decision, task=None)  # FK unpopulated, mimicking old rows

        self._run_migration()

        decision.refresh_from_db()
        assert decision.follow_up_created_at is not None  # kept
        assert decision.follow_up_task == task  # backfilled

    def test_backfilled_pledge_does_not_duplicate_on_next_sweep(self):
        # The whole point of backfill-before-heal: a pledge with a live Task must not
        # be re-armed (which would create a second follow-up).
        owner = UserFactory(role="missionary")
        contact, decision = _make_pledge(owner=owner, amount="100.00")
        Task.objects.create(
            owner=owner,
            contact=contact,
            title="Donation still not received — follow up",
            task_type=TaskType.FOLLOW_UP,
            status=TaskStatus.PENDING,
            due_date=timezone.now().date(),
        )
        self._latch(decision, task=None)

        self._run_migration()

        assert run_pledge_followup_sweep() == 0
        assert Task.objects.filter(task_type=TaskType.FOLLOW_UP).count() == 1

    def test_completed_task_is_treated_as_orphan_and_healed(self):
        # A completed/cancelled follow-up is not "live" — the pledge should heal so a
        # fresh follow-up can arise if still unfulfilled.
        owner = UserFactory(role="missionary")
        contact, decision = _make_pledge(owner=owner, amount="100.00")
        Task.objects.create(
            owner=owner,
            contact=contact,
            title="Donation still not received — follow up",
            task_type=TaskType.FOLLOW_UP,
            status=TaskStatus.COMPLETED,
            due_date=timezone.now().date(),
        )
        self._latch(decision, task=None)

        self._run_migration()

        decision.refresh_from_db()
        assert decision.follow_up_created_at is None

    def test_migration_is_noop_on_clean_data(self):
        # No latched decisions -> nothing changes, no crash.
        _make_pledge(amount="100.00")  # active pledge, no latch
        self._run_migration()
        assert Decision.objects.filter(follow_up_created_at__isnull=False).count() == 0


@pytest.mark.django_db
class TestIdempotency:
    """Re-running the sweep never duplicates follow-ups."""

    def test_second_run_creates_nothing(self):
        _make_pledge(amount="100.00")
        assert run_pledge_followup_sweep() == 1
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 1

    def test_already_stamped_pledge_is_skipped(self):
        _contact, decision = _make_pledge(amount="100.00")
        Decision.objects.filter(pk=decision.pk).update(follow_up_created_at=timezone.now())
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 0


@pytest.mark.django_db
class TestTiming:
    """The 10-day boundary."""

    def test_nine_days_old_not_yet_due(self):
        _make_pledge(amount="100.00", age_days=9)
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 0

    def test_exactly_ten_days_old_is_due(self):
        _make_pledge(amount="100.00", age_days=10)
        assert run_pledge_followup_sweep() == 1


@pytest.mark.django_db
class TestEligibility:
    """Status and merged-contact filtering."""

    @pytest.mark.parametrize(
        "status", [DecisionStatus.PENDING, DecisionStatus.PAUSED, DecisionStatus.DECLINED]
    )
    def test_non_active_pledges_ignored(self, status):
        _make_pledge(amount="100.00", status=status)
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 0

    def test_merged_contact_ignored(self):
        contact, _decision = _make_pledge(amount="100.00")
        Contact.objects.filter(pk=contact.pk).update(is_merged=True)
        assert run_pledge_followup_sweep() == 0
        assert Task.objects.count() == 0


@pytest.mark.django_db
class TestMultiplePledges:
    """Each pledge is evaluated independently."""

    def test_two_pledges_same_donor_evaluated_independently(self):
        owner = UserFactory(role="missionary")
        contact = ContactFactory(owner=owner)
        journal = Journal.objects.create(owner=owner, name="C", goal_amount="50000.00")

        aged = timezone.now() - timedelta(days=10)
        jc1 = JournalContact.objects.create(journal=journal, contact=contact)
        d1 = Decision.objects.create(
            journal_contact=jc1, amount="100.00", status=DecisionStatus.ACTIVE
        )
        # A second journal is needed because JournalContact is unique per (journal, contact).
        journal2 = Journal.objects.create(owner=owner, name="C2", goal_amount="50000.00")
        jc2 = JournalContact.objects.create(journal=journal2, contact=contact)
        d2 = Decision.objects.create(
            journal_contact=jc2, amount="200.00", status=DecisionStatus.ACTIVE
        )
        Decision.objects.filter(pk__in=[d1.pk, d2.pk]).update(created_at=aged)

        # A $100 gift fulfills d1 but not the $200 d2.
        GiftFactory(donor_contact=contact, amount_cents=10000, gift_date=timezone.now().date())

        assert run_pledge_followup_sweep() == 1
        d1.refresh_from_db()
        d2.refresh_from_db()
        assert d1.follow_up_created_at is None
        assert d2.follow_up_created_at is not None


@pytest.mark.django_db
class TestTriggers:
    """The management command and Celery task drive the same sweep."""

    def test_management_command_creates_followup(self):
        from django.core.management import call_command

        _make_pledge(amount="100.00")
        call_command("check_pledge_followups")
        assert Task.objects.count() == 1

    def test_management_command_dry_run_creates_nothing(self):
        from django.core.management import call_command

        _contact, decision = _make_pledge(amount="100.00")
        call_command("check_pledge_followups", "--dry-run")
        assert Task.objects.count() == 0
        decision.refresh_from_db()
        assert decision.follow_up_created_at is None

    def test_celery_task_creates_followup(self):
        from apps.journals.tasks import check_pledge_followups

        _make_pledge(amount="100.00")
        result = check_pledge_followups()
        assert "1" in result
        assert Task.objects.count() == 1
