"""
Celery tasks for contact management.
"""
from celery import shared_task


@shared_task
def detect_at_risk_donors():
    """
    Detect donors who are at risk of lapsing.
    At-risk means: has given multiple times but no gift in 60+ days.
    Run daily.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.contacts.models import Contact, ContactStatus
    from apps.events.models import Event, EventSeverity, EventType

    cutoff_date = timezone.now().date() - timedelta(days=60)

    # Find at-risk donors who haven't already been flagged recently
    at_risk_contacts = Contact.objects.filter(
        status=ContactStatus.DONOR,
        last_gift_date__lt=cutoff_date,
        gift_count__gte=2  # Has given at least twice
    ).exclude(
        # Exclude those we already notified in the last 30 days
        events__event_type=EventType.AT_RISK,
        events__created_at__gte=timezone.now() - timedelta(days=30)
    )

    at_risk_count = 0
    for contact in at_risk_contacts:
        # Create at-risk event for the contact owner
        Event.objects.create(
            user=contact.owner,
            event_type=EventType.AT_RISK,
            title=f'{contact.full_name} is at risk of lapsing',
            message=f'Last gift was on {contact.last_gift_date}. Consider reaching out.',
            severity=EventSeverity.WARNING,
            contact=contact,
            metadata={
                'last_gift_date': str(contact.last_gift_date),
                'days_since_last_gift': (timezone.now().date() - contact.last_gift_date).days,
                'total_given': str(contact.total_given),
            }
        )
        at_risk_count += 1

    return f'Identified {at_risk_count} at-risk donors'
