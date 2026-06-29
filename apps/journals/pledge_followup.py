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
        Task.objects.create(
            owner=contact.owner,
            contact=contact,
            title=FOLLOW_UP_TITLE,
            task_type=TaskType.FOLLOW_UP,
            status=TaskStatus.PENDING,
            auto_generated=True,
            due_date=today + timedelta(days=TASK_DUE_OFFSET_DAYS),
        )
        locked.follow_up_created_at = timezone.now()
        locked.save(update_fields=["follow_up_created_at", "updated_at"])
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
