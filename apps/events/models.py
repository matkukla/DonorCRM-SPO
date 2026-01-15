"""
Event model for audit trail and notifications.
"""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class EventType(models.TextChoices):
    """Types of events in the system."""
    # Donation events
    DONATION_RECEIVED = 'donation_received', 'Donation Received'
    FIRST_DONATION = 'first_donation', 'First Donation'

    # Pledge events
    PLEDGE_CREATED = 'pledge_created', 'Pledge Created'
    PLEDGE_UPDATED = 'pledge_updated', 'Pledge Updated'
    PLEDGE_LATE = 'pledge_late', 'Pledge Late'
    PLEDGE_CANCELLED = 'pledge_cancelled', 'Pledge Cancelled'

    # Contact events
    CONTACT_CREATED = 'contact_created', 'Contact Created'
    CONTACT_UPDATED = 'contact_updated', 'Contact Updated'
    CONTACT_STATUS_CHANGED = 'contact_status_changed', 'Contact Status Changed'

    # Alert events
    DONOR_LAPSED = 'donor_lapsed', 'Donor Lapsed'
    GIFT_LATE = 'gift_late', 'Gift Late'
    AT_RISK = 'at_risk', 'At Risk Donor'

    # Task events
    TASK_DUE = 'task_due', 'Task Due'
    TASK_OVERDUE = 'task_overdue', 'Task Overdue'
    TASK_COMPLETED = 'task_completed', 'Task Completed'

    # System events
    IMPORT_COMPLETED = 'import_completed', 'Import Completed'
    USER_LOGIN = 'user_login', 'User Login'


class EventSeverity(models.TextChoices):
    """Severity level of events."""
    INFO = 'info', 'Info'
    SUCCESS = 'success', 'Success'
    WARNING = 'warning', 'Warning'
    ALERT = 'alert', 'Alert'


class Event(TimeStampedModel):
    """
    Audit trail and notification feed entry.
    Uses GenericForeignKey to link to any model.
    """
    # Who this event is for (notification recipient)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events',
        db_index=True
    )

    # Event classification
    event_type = models.CharField(
        'type',
        max_length=30,
        choices=EventType.choices,
        db_index=True
    )

    severity = models.CharField(
        'severity',
        max_length=20,
        choices=EventSeverity.choices,
        default=EventSeverity.INFO
    )

    # Human-readable message
    title = models.CharField('title', max_length=255)
    message = models.TextField('message', blank=True)

    # Generic relation to source object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.UUIDField(null=True, blank=True, db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Optional direct contact link for quick access
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='events'
    )

    # Read/seen tracking
    is_read = models.BooleanField('read', default=False, db_index=True)
    read_at = models.DateTimeField('read at', null=True, blank=True)

    # For dashboard "What Changed" since last login
    is_new = models.BooleanField('new', default=True, db_index=True)

    # Additional context data (JSON)
    metadata = models.JSONField('metadata', default=dict, blank=True)

    class Meta:
        db_table = 'events'
        verbose_name = 'event'
        verbose_name_plural = 'events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['user', 'is_new']),
            models.Index(fields=['contact', 'created_at']),
        ]

    def __str__(self):
        return f'{self.event_type}: {self.title}'

    def mark_read(self):
        """Mark event as read."""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
