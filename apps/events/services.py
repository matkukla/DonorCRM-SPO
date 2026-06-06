"""
Service functions for events.
"""

from apps.events.models import Event


def mark_events_as_not_new(user):
    """Mark all events for user as not new (after viewing dashboard)."""
    Event.objects.filter(user=user, is_new=True).update(is_new=False)
