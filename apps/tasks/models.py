"""
Task model for reminders and action items.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class TaskPriority(models.TextChoices):
    """Priority level for tasks."""
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    URGENT = 'urgent', 'Urgent'


class TaskStatus(models.TextChoices):
    """Status of a task."""
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class TaskType(models.TextChoices):
    """Type of task."""
    CALL = 'call', 'Phone Call'
    EMAIL = 'email', 'Email'
    THANK_YOU = 'thank_you', 'Thank You'
    MEETING = 'meeting', 'Meeting'
    FOLLOW_UP = 'follow_up', 'Follow Up'
    OTHER = 'other', 'Other'


class Task(TimeStampedModel):
    """
    Action item or reminder, optionally linked to a contact.
    """
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
        db_index=True
    )

    # Optional contact link
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks'
    )

    # Task details
    title = models.CharField('title', max_length=255)
    description = models.TextField('description', blank=True)

    task_type = models.CharField(
        'type',
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.OTHER
    )

    priority = models.CharField(
        'priority',
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        db_index=True
    )

    status = models.CharField(
        'status',
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True
    )

    # Timing
    due_date = models.DateField('due date', db_index=True)
    due_time = models.TimeField('due time', null=True, blank=True)
    reminder_date = models.DateField('reminder date', null=True, blank=True)

    # Completion tracking
    completed_at = models.DateTimeField('completed at', null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_tasks'
    )

    # Auto-generated task tracking
    auto_generated = models.BooleanField('auto generated', default=False)
    source_event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_tasks'
    )

    class Meta:
        db_table = 'tasks'
        verbose_name = 'task'
        verbose_name_plural = 'tasks'
        ordering = ['due_date', '-priority', 'created_at']
        indexes = [
            models.Index(fields=['owner', 'status', 'due_date']),
            models.Index(fields=['owner', 'due_date']),
            models.Index(fields=['contact', 'status']),
            models.Index(fields=['status', 'due_date']),
        ]

    def __str__(self):
        return f'{self.title} (due: {self.due_date})'

    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        return self.due_date < timezone.now().date()

    def mark_complete(self, user):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save(update_fields=['status', 'completed_at', 'completed_by'])

    def mark_cancelled(self):
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.save(update_fields=['status'])
