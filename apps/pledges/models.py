"""
Pledge model for recurring giving commitments.
"""
from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class PledgeFrequency(models.TextChoices):
    """Frequency of pledge payments."""
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    SEMI_ANNUAL = 'semi_annual', 'Semi-Annual'
    ANNUAL = 'annual', 'Annual'


class PledgeStatus(models.TextChoices):
    """Status of a pledge."""
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class Pledge(TimeStampedModel):
    """
    Recurring giving commitment from a donor.
    Tracks expected vs actual fulfillment.
    """
    # Link to donor
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='pledges',
        db_index=True
    )

    # Pledge details
    amount = models.DecimalField(
        'amount',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Committed amount per frequency period'
    )

    frequency = models.CharField(
        'frequency',
        max_length=20,
        choices=PledgeFrequency.choices,
        default=PledgeFrequency.MONTHLY
    )

    status = models.CharField(
        'status',
        max_length=20,
        choices=PledgeStatus.choices,
        default=PledgeStatus.ACTIVE,
        db_index=True
    )

    # Timeline
    start_date = models.DateField('start date', db_index=True)
    end_date = models.DateField('end date', null=True, blank=True)

    # Tracking
    last_fulfilled_date = models.DateField('last fulfilled', null=True, blank=True)
    next_expected_date = models.DateField('next expected', null=True, blank=True, db_index=True)

    # Fulfillment stats (denormalized for performance)
    total_expected = models.DecimalField(
        'total expected',
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_received = models.DecimalField(
        'total received',
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Alert tracking
    is_late = models.BooleanField('is late', default=False, db_index=True)
    days_late = models.PositiveIntegerField('days late', default=0)
    late_notified_at = models.DateTimeField('late notified', null=True, blank=True)

    notes = models.TextField('notes', blank=True)

    class Meta:
        db_table = 'pledges'
        verbose_name = 'pledge'
        verbose_name_plural = 'pledges'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contact', 'status']),
            models.Index(fields=['status', 'next_expected_date']),
            models.Index(fields=['is_late']),
        ]

    def __str__(self):
        return f'${self.amount}/{self.get_frequency_display()} from {self.contact}'

    @property
    def monthly_equivalent(self):
        """Calculate monthly equivalent for support tracking."""
        multipliers = {
            PledgeFrequency.MONTHLY: 1,
            PledgeFrequency.QUARTERLY: 1 / 3,
            PledgeFrequency.SEMI_ANNUAL: 1 / 6,
            PledgeFrequency.ANNUAL: 1 / 12,
        }
        return float(self.amount) * multipliers.get(self.frequency, 1)

    @property
    def fulfillment_percentage(self):
        """Calculate percentage of pledge fulfilled."""
        if self.total_expected == 0:
            return 0
        return (float(self.total_received) / float(self.total_expected)) * 100

    def calculate_next_expected_date(self):
        """Calculate when next payment is expected."""
        if self.status != PledgeStatus.ACTIVE:
            return None

        base_date = self.last_fulfilled_date or self.start_date

        deltas = {
            PledgeFrequency.MONTHLY: relativedelta(months=1),
            PledgeFrequency.QUARTERLY: relativedelta(months=3),
            PledgeFrequency.SEMI_ANNUAL: relativedelta(months=6),
            PledgeFrequency.ANNUAL: relativedelta(years=1),
        }

        return base_date + deltas.get(self.frequency, relativedelta(months=1))

    def check_late_status(self, grace_days=10):
        """
        Check if pledge payment is late.
        Default grace period of 10 days.
        """
        if not self.next_expected_date or self.status != PledgeStatus.ACTIVE:
            self.is_late = False
            self.days_late = 0
            return

        today = timezone.now().date()
        expected_with_grace = self.next_expected_date + timedelta(days=grace_days)

        if today > expected_with_grace:
            self.is_late = True
            self.days_late = (today - self.next_expected_date).days
        else:
            self.is_late = False
            self.days_late = 0

    def record_fulfillment(self, donation):
        """Record that a donation fulfilled this pledge period."""
        self.last_fulfilled_date = donation.date
        self.total_received += donation.amount
        self.next_expected_date = self.calculate_next_expected_date()
        self.is_late = False
        self.days_late = 0
        self.save()

    def pause(self):
        """Pause the pledge."""
        self.status = PledgeStatus.PAUSED
        self.is_late = False
        self.days_late = 0
        self.save()

    def resume(self):
        """Resume a paused pledge."""
        self.status = PledgeStatus.ACTIVE
        self.next_expected_date = self.calculate_next_expected_date()
        self.save()

    def cancel(self):
        """Cancel the pledge."""
        self.status = PledgeStatus.CANCELLED
        self.end_date = timezone.now().date()
        self.is_late = False
        self.days_late = 0
        self.save()

    def save(self, *args, **kwargs):
        # Calculate next expected date for new active pledges
        if self._state.adding and self.status == PledgeStatus.ACTIVE:
            self.next_expected_date = self.calculate_next_expected_date()
        super().save(*args, **kwargs)
