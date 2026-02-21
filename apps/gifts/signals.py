"""
Signals for Gift model.

Mirrors the Donation signal handlers for contact stat updates and event
creation, adapted for the Gift model's field names (donor_contact, amount_dollars).
"""
import threading

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.gifts.models import Gift


_signal_state = threading.local()


def disable_gift_signals():
    """Disable gift signals during bulk operations."""
    _signal_state._skip_signals = True


def enable_gift_signals():
    """Re-enable gift signals after bulk operations."""
    _signal_state._skip_signals = False


def _signals_disabled():
    """Check if signals are currently disabled."""
    return getattr(_signal_state, '_skip_signals', False)


@receiver(post_save, sender=Gift)
def update_contact_stats_on_gift_save(sender, instance, created, **kwargs):
    """Update contact's giving stats when a gift is saved (both create and edit)."""
    if _signals_disabled():
        return

    # Always recalculate contact stats on both create and edit
    instance.donor_contact.update_giving_stats()

    # The following actions only apply to newly created gifts
    if created:
        # Mark contact as needing thank-you
        instance.donor_contact.needs_thank_you = True
        instance.donor_contact.save(update_fields=['needs_thank_you'])

        # Create event for new gift (uses existing DONATION_RECEIVED event type
        # to avoid orphaning existing events in the events table)
        from apps.events.models import Event, EventSeverity, EventType
        Event.objects.create(
            user=instance.donor_contact.owner,
            event_type=EventType.DONATION_RECEIVED,
            title=f'Gift from {instance.donor_contact.full_name}',
            message=f'${instance.amount_dollars} received',
            severity=EventSeverity.SUCCESS,
            contact=instance.donor_contact,
        )


@receiver(post_delete, sender=Gift)
def update_contact_stats_on_gift_delete(sender, instance, **kwargs):
    """Update contact's giving stats when a gift is deleted."""
    instance.donor_contact.update_giving_stats()
