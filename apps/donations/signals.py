"""
Signals for Donation model.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.donations.models import Donation


@receiver(post_save, sender=Donation)
def update_contact_stats_on_save(sender, instance, created, **kwargs):
    """Update contact's giving stats when donation is saved."""
    if not created:
        return

    # Update contact stats first
    instance.contact.update_giving_stats()

    # Mark contact as needing thank-you for new donations
    if not instance.thanked:
        instance.contact.needs_thank_you = True
        instance.contact.save(update_fields=['needs_thank_you'])

    # Update pledge fulfillment if linked to a pledge
    if instance.pledge:
        instance.pledge.record_fulfillment(instance)

    # Create event for new donations
    from apps.events.models import Event, EventType, EventSeverity
    Event.objects.create(
        user=instance.contact.owner,
        event_type=EventType.DONATION_RECEIVED,
        title=f'Donation from {instance.contact.full_name}',
        message=f'${instance.amount} received',
        severity=EventSeverity.SUCCESS,
        contact=instance.contact
    )


@receiver(post_delete, sender=Donation)
def update_contact_stats_on_delete(sender, instance, **kwargs):
    """Update contact's giving stats when donation is deleted."""
    instance.contact.update_giving_stats()
