"""
Signals for Pledge model state changes.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.pledges.models import Pledge, PledgeStatus


@receiver(pre_save, sender=Pledge)
def track_pledge_status_change(sender, instance, **kwargs):
    """Track status changes before save to detect transitions."""
    if instance.pk:
        try:
            old_instance = Pledge.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Pledge.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Pledge)
def handle_pledge_status_change(sender, instance, created, **kwargs):
    """Create events when pledge status changes."""
    from apps.events.models import Event, EventSeverity, EventType

    if created:
        # New pledge created
        Event.objects.create(
            user=instance.contact.owner,
            event_type=EventType.PLEDGE_CREATED,
            title=f'New pledge from {instance.contact.full_name}',
            message=f'${instance.amount}/{instance.get_frequency_display()} pledge created',
            severity=EventSeverity.SUCCESS,
            contact=instance.contact,
            metadata={
                'amount': str(instance.amount),
                'frequency': instance.frequency,
            }
        )
        return

    # Check for status change
    old_status = getattr(instance, '_old_status', None)
    if old_status and old_status != instance.status:
        _create_status_change_event(instance, old_status)


def _create_status_change_event(pledge, old_status):
    """Create event for pledge status change."""
    from apps.events.models import Event, EventSeverity, EventType

    status_messages = {
        PledgeStatus.PAUSED: {
            'event_type': EventType.PLEDGE_UPDATED,
            'title': f'Pledge paused: {pledge.contact.full_name}',
            'message': f'${pledge.amount}/{pledge.get_frequency_display()} pledge has been paused',
            'severity': EventSeverity.INFO,
        },
        PledgeStatus.ACTIVE: {
            'event_type': EventType.PLEDGE_UPDATED,
            'title': f'Pledge resumed: {pledge.contact.full_name}',
            'message': f'${pledge.amount}/{pledge.get_frequency_display()} pledge has been resumed',
            'severity': EventSeverity.SUCCESS,
        },
        PledgeStatus.CANCELLED: {
            'event_type': EventType.PLEDGE_CANCELLED,
            'title': f'Pledge cancelled: {pledge.contact.full_name}',
            'message': f'${pledge.amount}/{pledge.get_frequency_display()} pledge has been cancelled',
            'severity': EventSeverity.WARNING,
        },
        PledgeStatus.COMPLETED: {
            'event_type': EventType.PLEDGE_UPDATED,
            'title': f'Pledge completed: {pledge.contact.full_name}',
            'message': f'${pledge.amount}/{pledge.get_frequency_display()} pledge has been marked as completed',
            'severity': EventSeverity.SUCCESS,
        },
    }

    event_info = status_messages.get(pledge.status)
    if event_info:
        Event.objects.create(
            user=pledge.contact.owner,
            event_type=event_info['event_type'],
            title=event_info['title'],
            message=event_info['message'],
            severity=event_info['severity'],
            contact=pledge.contact,
            metadata={
                'old_status': old_status,
                'new_status': pledge.status,
                'amount': str(pledge.amount),
                'frequency': pledge.frequency,
            }
        )
