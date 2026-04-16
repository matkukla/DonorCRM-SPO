"""
Utilities for generating Gift payment records from RecurringGift commitments.

Provides date generation, external ID creation, and sync logic for keeping
Gift records in sync with their source RecurringGift.
"""
import logging
from datetime import date

from dateutil.relativedelta import relativedelta

from apps.gifts.models import RecurringGiftFrequency, RecurringGiftStatus

logger = logging.getLogger(__name__)

# Safety cap to prevent runaway loops (e.g. weekly pledge from year 2000)
MAX_PAYMENT_DATES = 2000


# Mapping of frequency to relativedelta step
FREQUENCY_DELTAS = {
    RecurringGiftFrequency.MONTHLY: relativedelta(months=1),
    RecurringGiftFrequency.QUARTERLY: relativedelta(months=3),
    RecurringGiftFrequency.SEMI_ANNUALLY: relativedelta(months=6),
    RecurringGiftFrequency.ANNUALLY: relativedelta(years=1),
    RecurringGiftFrequency.BIMONTHLY: relativedelta(months=2),
    RecurringGiftFrequency.BIWEEKLY: relativedelta(weeks=2),
    RecurringGiftFrequency.WEEKLY: relativedelta(weeks=1),
}

# Frequencies that can have multiple payments per month need full-date IDs
SUB_MONTHLY_FREQUENCIES = {
    RecurringGiftFrequency.BIWEEKLY,
    RecurringGiftFrequency.WEEKLY,
}


def generate_payment_dates(start_date, end_date, frequency, cutoff_date=None):
    """
    Generate a list of payment dates for a recurring gift.

    Args:
        start_date: First payment date
        end_date: Last possible payment date (None = no end)
        frequency: RecurringGiftFrequency value
        cutoff_date: Don't generate dates beyond this (defaults to today)

    Returns:
        List of date objects, one per expected payment
    """
    if frequency == RecurringGiftFrequency.IRREGULAR:
        return []

    delta = FREQUENCY_DELTAS.get(frequency)
    if delta is None:
        return []

    if cutoff_date is None:
        cutoff_date = date.today()

    # Cap at end_date if provided
    effective_end = cutoff_date
    if end_date and end_date < effective_end:
        effective_end = end_date

    dates = []
    current = start_date
    while current <= effective_end:
        dates.append(current)
        if len(dates) >= MAX_PAYMENT_DATES:
            logger.warning(
                "Hit max payment dates (%d) — start_date=%s frequency=%s",
                MAX_PAYMENT_DATES,
                start_date,
                frequency,
            )
            break
        current = current + delta

    return dates


def make_recurring_external_id(rg_external_id, payment_date, frequency):
    """
    Create a deterministic external_gift_id for a recurring payment Gift.

    Uses YYYY-MM for monthly+ frequencies, YYYY-MM-DD for sub-monthly
    (weekly/biweekly) to avoid collisions.
    """
    if frequency in SUB_MONTHLY_FREQUENCIES:
        return f"rg_{rg_external_id}_{payment_date.strftime('%Y-%m-%d')}"
    return f"rg_{rg_external_id}_{payment_date.strftime('%Y-%m')}"


def _build_gift_objects(rg, payment_dates, rg_ext_id, existing_ext_ids):
    """Build Gift objects for payment dates that don't already exist."""
    from apps.gifts.models import Gift

    gifts = []
    for pd in payment_dates:
        ext_id = make_recurring_external_id(rg_ext_id, pd, rg.frequency)
        if ext_id not in existing_ext_ids:
            gifts.append(
                Gift(
                    donor_contact=rg.donor_contact,
                    fund=rg.fund,
                    recurring_gift=rg,
                    external_gift_id=ext_id,
                    amount_cents=rg.amount_cents,
                    gift_date=pd,
                    payment_type=rg.payment_type,
                    description=f"Recurring payment ({rg.get_frequency_display()})",
                )
            )
    return gifts


def generate_gifts_for_recurring(recurring_gift, cutoff_date=None):
    """
    Create Gift records for each payment period of a RecurringGift.

    Uses bulk_create with ignore_conflicts for idempotency.
    Signals should be disabled by the caller.

    Returns:
        Number of Gift records created
    """
    from apps.gifts.models import Gift

    if recurring_gift.frequency == RecurringGiftFrequency.IRREGULAR:
        return 0

    rg_ext_id = recurring_gift.external_gift_id or str(recurring_gift.pk)

    payment_dates = generate_payment_dates(
        start_date=recurring_gift.start_date,
        end_date=recurring_gift.end_date,
        frequency=recurring_gift.frequency,
        cutoff_date=cutoff_date,
    )

    if not payment_dates:
        return 0

    # Build external IDs and check which already exist
    ext_ids = [
        make_recurring_external_id(rg_ext_id, pd, recurring_gift.frequency) for pd in payment_dates
    ]
    existing_ext_ids = set(
        Gift.objects.filter(external_gift_id__in=ext_ids).values_list("external_gift_id", flat=True)
    )

    gifts_to_create = _build_gift_objects(
        recurring_gift, payment_dates, rg_ext_id, existing_ext_ids
    )

    if gifts_to_create:
        Gift.objects.bulk_create(gifts_to_create, ignore_conflicts=True)

    return len(gifts_to_create)


def sync_recurring_gift_payments(recurring_gift, cutoff_date=None):
    """
    Sync Gift records for a RecurringGift after it's been edited.

    - Creates missing Gift records for valid payment dates
    - Updates amount_cents on existing linked Gifts if amount changed
    - Deletes linked Gifts beyond the new end_date
    - Calls update_giving_stats() on the contact

    Signals should be disabled by the caller or this function handles it.
    """
    from apps.gifts.models import Gift
    from apps.gifts.signals import disable_gift_signals, enable_gift_signals

    disable_gift_signals()
    try:
        rg = recurring_gift

        # Statuses that mean no more payments should exist
        STOPPED_STATUSES = {
            RecurringGiftStatus.CANCELLED,
            RecurringGiftStatus.TERMINATED,
            RecurringGiftStatus.COMPLETED,
        }
        if rg.status in STOPPED_STATUSES:
            Gift.objects.filter(recurring_gift=rg).delete()
            rg.donor_contact.update_giving_stats()
            return

        # Held: keep existing payments but don't generate new ones
        if rg.status == RecurringGiftStatus.HELD:
            rg.donor_contact.update_giving_stats()
            return

        rg_ext_id = rg.external_gift_id or str(rg.pk)

        if rg.frequency == RecurringGiftFrequency.IRREGULAR:
            # Can't generate payments for irregular — leave existing ones
            return

        payment_dates = generate_payment_dates(
            start_date=rg.start_date,
            end_date=rg.end_date,
            frequency=rg.frequency,
            cutoff_date=cutoff_date,
        )

        valid_ext_ids = set(
            make_recurring_external_id(rg_ext_id, pd, rg.frequency) for pd in payment_dates
        )

        # Delete gifts beyond valid range (e.g., end_date shortened)
        Gift.objects.filter(recurring_gift=rg).exclude(external_gift_id__in=valid_ext_ids).delete()

        # Update amount and payment_type on existing gifts if they changed
        Gift.objects.filter(recurring_gift=rg).exclude(
            amount_cents=rg.amount_cents, payment_type=rg.payment_type
        ).update(amount_cents=rg.amount_cents, payment_type=rg.payment_type)

        # Create missing gifts
        existing_ext_ids = set(
            Gift.objects.filter(recurring_gift=rg).values_list("external_gift_id", flat=True)
        )

        gifts_to_create = _build_gift_objects(rg, payment_dates, rg_ext_id, existing_ext_ids)
        if gifts_to_create:
            Gift.objects.bulk_create(gifts_to_create, ignore_conflicts=True)

        rg.donor_contact.update_giving_stats()
    finally:
        enable_gift_signals()
