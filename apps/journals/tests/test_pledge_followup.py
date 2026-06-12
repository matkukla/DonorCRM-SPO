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
from apps.journals.pledge_followup import is_pledge_fulfilled, run_pledge_followup_sweep
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
