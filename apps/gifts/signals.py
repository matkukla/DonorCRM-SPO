"""
Signals for Gift model.

Mirrors the Donation signal handlers for contact stat updates and event
creation, adapted for the Gift model's field names (donor_contact, amount_dollars).
"""

import threading
from contextlib import contextmanager

from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from apps.gifts.models import Gift, RecurringGift

_signal_state = threading.local()


def disable_gift_signals():
    """Disable gift signals during bulk operations. Re-entrant safe (uses counter)."""
    _signal_state._skip_count = getattr(_signal_state, "_skip_count", 0) + 1


def enable_gift_signals():
    """Re-enable gift signals after bulk operations. Re-entrant safe (uses counter)."""
    _signal_state._skip_count = max(0, getattr(_signal_state, "_skip_count", 0) - 1)


def _signals_disabled():
    """Check if signals are currently disabled."""
    return getattr(_signal_state, "_skip_count", 0) > 0


@contextmanager
def gift_signals_disabled():
    """Context-manager form of :func:`disable_gift_signals`.

    Guarantees re-enable on every exit path (including exceptions), so a bulk
    importer that suppresses signals can never leak the disabled state into the
    thread-local counter for the next request handled by this worker thread.
    """
    disable_gift_signals()
    try:
        yield
    finally:
        enable_gift_signals()


def recompute_giving_stats(contact_ids):
    """Recompute giving stats once per contact after a bulk gift import.

    Bulk gift importers call :func:`disable_gift_signals`, create all gifts,
    then call this once. That collapses the per-save signal cascade
    (``update_giving_stats`` ~5-7 queries on *every* ``Gift.objects.create``)
    down to a single recompute per affected contact, which keeps a large
    synchronous import inside the request timeout. ``update_giving_stats`` is a
    from-scratch aggregate, so one call reflects every gift just created.

    Must be called inside the importer's ``transaction.atomic()`` so the
    recompute sees the uncommitted gifts and commits atomically with them.
    """
    from apps.contacts.models import Contact

    for contact in Contact.objects.filter(id__in=contact_ids):
        contact.update_giving_stats()


def enqueue_thank_you_for_recent_imports(contact_ids, days=None):
    """Flag imported contacts for the Thank You Queue when their gift is recent.

    Bulk importers disable gift signals, so the UI signal's "new non-recurring
    gift enqueues a thank-you" rule (update_contact_stats_on_gift_save) never
    fires on import. Without this, every imported gift is silently excluded from
    the Thank You Queue (F4, ADR 0006).

    A contact is flagged when it has at least one **non-recurring** gift dated
    within the last ``days`` (default: the shared 60-day window). Historical
    backfill (older gifts) does NOT enqueue, so a multi-year history dump
    doesn't flood the queue. Recurring auto-payments are never re-thanked.

    Call AFTER recompute_giving_stats, inside the importer's atomic block.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.contacts.last_contacted import NOT_CONTACTED_RECENTLY_DAYS
    from apps.contacts.models import Contact

    if days is None:
        days = NOT_CONTACTED_RECENTLY_DAYS

    cutoff = timezone.localdate() - timedelta(days=days)
    recent_contact_ids = (
        Gift.objects.filter(
            donor_contact_id__in=contact_ids,
            recurring_gift__isnull=True,
            gift_date__gte=cutoff,
        )
        .values_list("donor_contact_id", flat=True)
        .distinct()
    )
    Contact.objects.filter(id__in=list(recent_contact_ids)).update(needs_thank_you=True)


@receiver(post_save, sender=Gift)
def update_contact_stats_on_gift_save(sender, instance, created, **kwargs):
    """Update contact's giving stats when a gift is saved (both create and edit)."""
    if _signals_disabled():
        return

    # Always recalculate contact stats on both create and edit
    instance.donor_contact.update_giving_stats()

    # Skip notifications for system-generated recurring payment records
    if instance.recurring_gift_id:
        return

    # The following actions only apply to newly created gifts
    if created:
        # Mark contact as needing thank-you
        instance.donor_contact.needs_thank_you = True
        instance.donor_contact.save(update_fields=["needs_thank_you"])

        # Create event for new gift (uses existing DONATION_RECEIVED event type
        # to avoid orphaning existing events in the events table)
        from apps.events.models import Event, EventSeverity, EventType

        Event.objects.create(
            user=instance.donor_contact.owner,
            event_type=EventType.DONATION_RECEIVED,
            title=f"Gift from {instance.donor_contact.full_name}",
            message=f"${instance.amount_dollars} received",
            severity=EventSeverity.SUCCESS,
            contact=instance.donor_contact,
        )


@receiver(post_delete, sender=Gift)
def update_contact_stats_on_gift_delete(sender, instance, **kwargs):
    """Update contact's giving stats when a gift is deleted."""
    instance.donor_contact.update_giving_stats()


@receiver(post_save, sender=RecurringGift)
def sync_gifts_on_recurring_gift_update(sender, instance, created, **kwargs):
    """Re-sync payment Gift records when a recurring gift commitment is edited.

    Only triggers sync when payment-relevant fields change (amount, frequency,
    dates, status). Skips on trivial updates like description edits.
    """
    if _signals_disabled():
        return
    if not created:
        PAYMENT_FIELDS = {
            "amount_cents",
            "frequency",
            "start_date",
            "end_date",
            "status",
            "payment_type",
        }
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and not PAYMENT_FIELDS.intersection(update_fields):
            return
        from apps.gifts.recurring_utils import sync_recurring_gift_payments

        sync_recurring_gift_payments(instance)


@receiver(pre_delete, sender=RecurringGift)
def delete_gifts_on_recurring_gift_delete(sender, instance, **kwargs):
    """Delete generated Gift records before a recurring gift is deleted.

    Uses pre_delete because Gift.recurring_gift has on_delete=SET_NULL,
    which would null the FK before post_delete fires.
    """
    Gift.objects.filter(recurring_gift=instance).delete()


@receiver(post_delete, sender=RecurringGift)
def update_contact_on_recurring_gift_delete(sender, instance, **kwargs):
    """Update contact stats after recurring gift and its generated gifts are deleted."""
    instance.donor_contact.update_giving_stats()
