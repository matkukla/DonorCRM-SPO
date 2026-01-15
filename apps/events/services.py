"""
Service functions for creating events.
"""
from django.contrib.contenttypes.models import ContentType

from apps.events.models import Event, EventSeverity, EventType


def create_event(user, event_type, title, message='', severity=EventSeverity.INFO,
                 content_object=None, contact=None, metadata=None):
    """
    Create a new event notification.
    """
    event = Event(
        user=user,
        event_type=event_type,
        title=title,
        message=message,
        severity=severity,
        contact=contact,
        metadata=metadata or {}
    )

    if content_object:
        event.content_type = ContentType.objects.get_for_model(content_object)
        event.object_id = content_object.id

    event.save()
    return event


def create_donation_event(donation):
    """Create event for new donation received."""
    # Use the contact from the donation (already updated by signal)
    contact = donation.contact
    # Refresh to get the updated gift_count from database
    contact.refresh_from_db()
    is_first = contact.gift_count == 1

    event_type = EventType.FIRST_DONATION if is_first else EventType.DONATION_RECEIVED
    severity = EventSeverity.SUCCESS

    title = f'{"First donation" if is_first else "Donation"} from {contact.full_name}'
    message = f'${donation.amount} received on {donation.date}'

    return create_event(
        user=contact.owner,
        event_type=event_type,
        title=title,
        message=message,
        severity=severity,
        content_object=donation,
        contact=contact,
        metadata={'amount': str(donation.amount), 'date': str(donation.date)}
    )


def create_pledge_late_event(pledge):
    """Create event for late pledge payment."""
    contact = pledge.contact

    return create_event(
        user=contact.owner,
        event_type=EventType.PLEDGE_LATE,
        title=f'Late pledge from {contact.full_name}',
        message=f'${pledge.amount}/{pledge.get_frequency_display()} pledge is {pledge.days_late} days late',
        severity=EventSeverity.WARNING,
        content_object=pledge,
        contact=contact,
        metadata={'days_late': pledge.days_late, 'amount': str(pledge.amount)}
    )


def create_at_risk_event(contact):
    """Create event for at-risk donor."""
    return create_event(
        user=contact.owner,
        event_type=EventType.AT_RISK,
        title=f'{contact.full_name} may be at risk',
        message=f'No donation in over 60 days. Last gift: {contact.last_gift_date}',
        severity=EventSeverity.WARNING,
        content_object=contact,
        contact=contact,
        metadata={'last_gift_date': str(contact.last_gift_date)}
    )


def create_contact_event(contact, event_type, title, message=''):
    """Create event for contact changes."""
    return create_event(
        user=contact.owner,
        event_type=event_type,
        title=title,
        message=message,
        severity=EventSeverity.INFO,
        content_object=contact,
        contact=contact
    )


def mark_events_as_not_new(user):
    """Mark all events for user as not new (after viewing dashboard)."""
    Event.objects.filter(user=user, is_new=True).update(is_new=False)
