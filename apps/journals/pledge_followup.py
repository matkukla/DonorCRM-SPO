"""
Pledge follow-up sweep.

A pledge is a ``Decision`` in the ``active`` state. Ten days after the pledge is
recorded (``Decision.created_at``), this sweep checks whether the pledge has been
fulfilled. If not, it creates exactly one follow-up Task for the owning missionary.

Fulfillment rule: the donor has a single Gift dated on/after the pledge date whose
amount is at least the pledged amount, OR an active recurring gift. Partial gifts do
not fulfill. Reversals (refunds / gift deletion after fulfillment) are out of scope.

The logic lives here, decoupled from how it is triggered. It is invoked by both a
Celery beat task (``apps.journals.tasks.check_pledge_followups``) and a management
command (``check_pledge_followups``).
"""

import logging
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

CHECK_DELAY_DAYS = 10
TASK_DUE_OFFSET_DAYS = 3
FOLLOW_UP_TITLE = "Donation still not received — follow up"


def is_pledge_fulfilled(decision) -> bool:
    """Return True if the donor has satisfied the pledge.

    Fulfilled when the donor has an active recurring gift, or a single gift dated on
    or after the pledge date whose amount is at least the pledged amount. Partial
    gifts that do not individually meet the amount do not count.
    """
    contact = decision.journal_contact.contact
    if contact.has_active_recurring_gift:
        return True

    pledge_date = decision.created_at.date()
    # decision.amount is a Decimal (dollars). Quantize to whole cents with
    # half-up rounding before converting to int, so the comparison against the
    # integer-cents Gift.amount_cents is exact and never truncates a fraction.
    amount_cents = int((decision.amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return contact.gifts.filter(
        gift_date__gte=pledge_date,
        amount_cents__gte=amount_cents,
    ).exists()


def _create_followup(decision, today: date) -> bool:
    """Create the follow-up Task for an unfulfilled pledge, idempotently.

    Re-reads the Decision under a row lock and re-checks the idempotency guard so two
    concurrent sweeps cannot both create a Task. Returns True if a Task was created.
    """
    from apps.journals.models import Decision
    from apps.tasks.models import Task, TaskStatus, TaskType

    with transaction.atomic():
        locked = (
            Decision.objects.select_for_update()
            .select_related("journal_contact__contact")
            .get(pk=decision.pk)
        )
        if locked.follow_up_created_at is not None:
            return False

        contact = locked.journal_contact.contact
        task = Task.objects.create(
            owner=contact.owner,
            contact=contact,
            title=FOLLOW_UP_TITLE,
            task_type=TaskType.FOLLOW_UP,
            status=TaskStatus.PENDING,
            auto_generated=True,
            due_date=today + timedelta(days=TASK_DUE_OFFSET_DAYS),
        )
        # Latch + FK are two halves of one fact ("this pledge has a live follow-up
        # Task"). Set them together; release_followup() clears them together.
        locked.follow_up_created_at = timezone.now()
        locked.follow_up_task = task
        locked.save(update_fields=["follow_up_created_at", "follow_up_task", "updated_at"])
    return True


def release_followup(task) -> bool:
    """Clear the follow-up latch when its Task is deleted, re-arming the sweep.

    Finds the Decision whose follow_up_task is this Task and nulls both halves of
    the latch (follow_up_created_at + follow_up_task), so a later sweep may create a
    fresh follow-up if the pledge is still unfulfilled. A no-op for Tasks that are
    not a pledge follow-up (the common case, since this fires on every Task delete).

    Must be called from a ``pre_delete`` signal: the follow_up_task FK is
    ``on_delete=SET_NULL``, so by ``post_delete`` Django has already nulled it and
    the lookup below would find nothing. (Same constraint the RecurringGift handler
    in apps/gifts/signals.py documents.) Runs inside the ambient delete transaction
    via a savepoint, so a rolled-back delete rolls back the latch clear too.

    Returns True if a latch was cleared.
    """
    from apps.journals.models import Decision

    with transaction.atomic():
        decision = Decision.objects.select_for_update().filter(follow_up_task=task).first()
        if decision is None:
            return False
        decision.follow_up_created_at = None
        decision.follow_up_task = None
        decision.save(update_fields=["follow_up_created_at", "follow_up_task", "updated_at"])
    return True


def discard_followup(decision) -> bool:
    """Delete the follow-up Task when its owning Decision is being deleted.

    The inverse of ``release_followup``: that verb handles the Task being deleted (and
    re-arms the sweep); this one handles the *Decision* being deleted (contact merge at
    apps/contacts/services.py, or a JournalContact cascade). Without this, the
    auto-generated follow-up Task would be orphaned — left open forever, referencing a
    pledge that no longer exists (issue #183).

    Must be called from a ``pre_delete`` signal on Decision: ``follow_up_task`` is
    ``on_delete=SET_NULL``, so by the time the Decision row is gone the FK is already
    nulled and the Task could not be found. Deleting the Task here still fires the Task
    ``pre_delete`` handler (``release_followup``); it clears the latch on the
    still-present (mid-delete) Decision row, which is harmless — the Decision is on its
    way out.

    Returns True if a follow-up Task was deleted.
    """
    from apps.tasks.models import Task

    # Read the FK straight from the DB rather than trusting the in-memory instance:
    # the sweep sets follow_up_task on a separately-locked row, so a Decision loaded
    # before the sweep would carry a stale (None) cached FK. values_list avoids
    # fetching the whole Decision.
    task_id = (
        type(decision)
        .objects.filter(pk=decision.pk)
        .values_list("follow_up_task_id", flat=True)
        .first()
    )
    if task_id is None:
        return False
    Task.objects.filter(pk=task_id).delete()
    return True


def run_pledge_followup_sweep(today: date | None = None, dry_run: bool = False) -> int:
    """Find unfulfilled pledges past their 10-day mark and create follow-up Tasks.

    Returns the number of follow-ups created (or, in dry-run mode, the number that
    would be created).
    """
    from apps.contacts.models import Contact
    from apps.journals.models import Decision, DecisionStatus

    today = today or timezone.now().date()
    cutoff = today - timedelta(days=CHECK_DELAY_DAYS)

    # Eligible: active pledge, past the 10-day mark, not yet followed up, donor not
    # merged. Contact.active filters is_merged=False; hard-deleted donors drop out via
    # the CASCADE on JournalContact.
    due = Decision.objects.filter(
        status=DecisionStatus.ACTIVE,
        follow_up_created_at__isnull=True,
        created_at__date__lte=cutoff,
        journal_contact__contact__in=Contact.active.all(),
    ).select_related("journal_contact__contact")

    logger.info("Starting pledge follow-up sweep (cutoff=%s, dry_run=%s)", cutoff, dry_run)

    created = 0
    for decision in due.iterator():
        if is_pledge_fulfilled(decision):
            continue
        if dry_run:
            created += 1
            continue
        if _create_followup(decision, today):
            created += 1

    logger.info("Pledge follow-up sweep completed: %d follow-up(s) created", created)
    return created
