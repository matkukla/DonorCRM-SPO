"""
Signals for Gift model.

Mirrors the Donation signal handlers for contact stat updates and event
creation, adapted for the Gift model's field names (donor_contact, amount_dollars).
"""

import threading

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
