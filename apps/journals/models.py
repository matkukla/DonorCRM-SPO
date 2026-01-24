"""
Journal models for donor engagement tracking.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class PipelineStage(models.TextChoices):
    """Six-stage donor engagement pipeline."""
    CONTACT = 'contact', 'Contact'
    MEET = 'meet', 'Meet'
    CLOSE = 'close', 'Close'
    DECISION = 'decision', 'Decision'
    THANK = 'thank', 'Thank'
    NEXT_STEPS = 'next_steps', 'Next Steps'


class StageEventType(models.TextChoices):
    """Typed events for stage activity logging."""
    # Communication events
    CALL_LOGGED = 'call_logged', 'Call Logged'
    EMAIL_SENT = 'email_sent', 'Email Sent'
    TEXT_SENT = 'text_sent', 'Text Sent'
    LETTER_SENT = 'letter_sent', 'Letter Sent'

    # Meeting events
    MEETING_SCHEDULED = 'meeting_scheduled', 'Meeting Scheduled'
    MEETING_COMPLETED = 'meeting_completed', 'Meeting Completed'

    # Ask/close events
    ASK_MADE = 'ask_made', 'Ask Made'

    # Follow-up events
    FOLLOW_UP_SCHEDULED = 'follow_up_scheduled', 'Follow-up Scheduled'
    FOLLOW_UP_COMPLETED = 'follow_up_completed', 'Follow-up Completed'

    # Decision events
    DECISION_RECEIVED = 'decision_received', 'Decision Received'

    # Thank/next events
    THANK_YOU_SENT = 'thank_you_sent', 'Thank You Sent'
    NEXT_STEP_CREATED = 'next_step_created', 'Next Step Created'

    # Generic
    NOTE_ADDED = 'note_added', 'Note Added'
    OTHER = 'other', 'Other'


class Journal(TimeStampedModel):
    """
    Fundraising journal tracking donor engagement campaign.
    Each journal has a goal, deadline, and contains multiple contacts.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='journals',
        db_index=True,
        help_text='Missionary who owns this journal'
    )

    name = models.CharField(
        'name',
        max_length=255,
        help_text='Journal name (e.g., "Q1 2025 Campaign")'
    )

    goal_amount = models.DecimalField(
        'goal amount',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Fundraising goal for this journal'
    )

    deadline = models.DateField(
        'deadline',
        null=True,
        blank=True,
        help_text='Target completion date'
    )

    is_archived = models.BooleanField(
        'archived',
        default=False,
        db_index=True
    )

    archived_at = models.DateTimeField(
        'archived at',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'journals'
        verbose_name = 'journal'
        verbose_name_plural = 'journals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_archived']),
        ]

    def __str__(self):
        return self.name

    def archive(self):
        """Archive this journal."""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=['is_archived', 'archived_at', 'updated_at'])


class JournalContact(TimeStampedModel):
    """
    Through-table linking journals to contacts.
    Each contact can be in multiple journals, each journal can have multiple contacts.
    """
    journal = models.ForeignKey(
        'Journal',
        on_delete=models.CASCADE,
        related_name='journal_contacts',
        db_index=True
    )

    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='journal_memberships',
        db_index=True
    )

    class Meta:
        db_table = 'journal_contacts'
        verbose_name = 'journal contact'
        verbose_name_plural = 'journal contacts'
        unique_together = [['journal', 'contact']]
        indexes = [
            models.Index(fields=['journal', 'contact']),
        ]

    def __str__(self):
        return f'{self.contact} in {self.journal}'


class JournalStageEvent(TimeStampedModel):
    """
    Append-only event log for pipeline stage activity.
    Records every interaction, note, and stage change for a contact in a journal.
    """
    journal_contact = models.ForeignKey(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='stage_events',
        db_index=True
    )

    stage = models.CharField(
        'stage',
        max_length=20,
        choices=PipelineStage.choices,
        db_index=True,
        help_text='Pipeline stage where event occurred'
    )

    event_type = models.CharField(
        'event type',
        max_length=30,
        choices=StageEventType.choices,
        db_index=True,
        help_text='Type of event/action'
    )

    notes = models.TextField(
        'notes',
        blank=True,
        help_text='Optional notes about this event'
    )

    metadata = models.JSONField(
        'metadata',
        default=dict,
        blank=True,
        help_text='Additional structured data (task ID, contact method, etc.)'
    )

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_stage_events',
        help_text='User who triggered this event'
    )

    class Meta:
        db_table = 'journal_stage_events'
        verbose_name = 'journal stage event'
        verbose_name_plural = 'journal stage events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journal_contact', 'stage', 'created_at']),
            models.Index(fields=['journal_contact', 'created_at']),
        ]

    def __str__(self):
        return f'{self.stage} - {self.event_type}'


class DecisionCadence(models.TextChoices):
    """Frequency options for recurring pledges."""
    ONE_TIME = 'one_time', 'One-Time'
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    ANNUAL = 'annual', 'Annual'


class DecisionStatus(models.TextChoices):
    """Status options for donor decisions."""
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    DECLINED = 'declined', 'Declined'


class Decision(TimeStampedModel):
    """
    Current decision state for a journal contact (mutable).
    Enforces one decision per journal_contact.
    """
    journal_contact = models.ForeignKey(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='decisions',
        db_index=True
    )

    amount = models.DecimalField(
        'amount',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Pledged amount'
    )

    cadence = models.CharField(
        'cadence',
        max_length=20,
        choices=DecisionCadence.choices,
        default=DecisionCadence.MONTHLY
    )

    status = models.CharField(
        'status',
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.PENDING,
        db_index=True
    )

    class Meta:
        db_table = 'journal_decisions'
        verbose_name = 'decision'
        verbose_name_plural = 'decisions'
        constraints = [
            models.UniqueConstraint(
                fields=['journal_contact'],
                name='unique_decision_per_journal_contact'
            )
        ]

    def __str__(self):
        return f'{self.journal_contact} - {self.amount} ({self.cadence})'

    @property
    def monthly_equivalent(self):
        """Calculate normalized monthly value for this decision."""
        multipliers = {
            DecisionCadence.ONE_TIME: Decimal('0'),
            DecisionCadence.MONTHLY: Decimal('1'),
            DecisionCadence.QUARTERLY: Decimal('1') / Decimal('3'),
            DecisionCadence.ANNUAL: Decimal('1') / Decimal('12'),
        }
        multiplier = multipliers[self.cadence]
        return round(self.amount * multiplier, 2)


class DecisionHistory(TimeStampedModel):
    """
    Append-only history of decision changes.
    Records what changed, when, and by whom.
    """
    decision = models.ForeignKey(
        'Decision',
        on_delete=models.CASCADE,
        related_name='history',
        db_index=True
    )

    changed_fields = models.JSONField(
        'changed fields',
        help_text='Mapping of field names to old values before change'
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='decision_changes'
    )

    class Meta:
        db_table = 'journal_decision_history'
        verbose_name = 'decision history'
        verbose_name_plural = 'decision histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['decision', '-created_at']),
        ]

    def __str__(self):
        return f'History for {self.decision} at {self.created_at}'
