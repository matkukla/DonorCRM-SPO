"""
Donation model for tracking individual gifts.
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class DonationType(models.TextChoices):
    """Type of donation."""
    ONE_TIME = 'one_time', 'One-Time Gift'
    RECURRING = 'recurring', 'Recurring Gift'
    SPECIAL = 'special', 'Special Gift'


class PaymentMethod(models.TextChoices):
    """Payment method for donation."""
    CHECK = 'check', 'Check'
    CASH = 'cash', 'Cash'
    CREDIT_CARD = 'credit_card', 'Credit Card'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer/ACH'
    OTHER = 'other', 'Other'


class Donation(TimeStampedModel):
    """
    Individual gift record linked to a contact.
    May be associated with a pledge if recurring.
    """
    # Link to donor
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='donations',
        db_index=True
    )

    # Optional link to pledge (for recurring gifts)
    pledge = models.ForeignKey(
        'pledges.Pledge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations'
    )

    # Gift details
    amount = models.DecimalField('amount', max_digits=10, decimal_places=2)
    date = models.DateField('date', db_index=True)

    donation_type = models.CharField(
        'type',
        max_length=20,
        choices=DonationType.choices,
        default=DonationType.ONE_TIME
    )

    payment_method = models.CharField(
        'payment method',
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CHECK
    )

    # Reference info (for imports/external systems)
    external_id = models.CharField(
        'external ID',
        max_length=100,
        blank=True,
        db_index=True,
        help_text='Reference ID from external system'
    )

    # Thank-you tracking
    thanked = models.BooleanField('thanked', default=False, db_index=True)
    thanked_at = models.DateTimeField('thanked at', null=True, blank=True)
    thanked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='thanked_donations'
    )

    notes = models.TextField('notes', blank=True)

    # Import tracking
    imported_at = models.DateTimeField('imported at', null=True, blank=True)
    import_batch = models.CharField('import batch', max_length=100, blank=True, db_index=True)

    class Meta:
        db_table = 'donations'
        verbose_name = 'donation'
        verbose_name_plural = 'donations'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['contact', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['thanked']),
            models.Index(fields=['import_batch']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['external_id'],
                name='unique_external_donation_id',
                condition=~models.Q(external_id='')
            )
        ]

    def __str__(self):
        return f'${self.amount} from {self.contact} on {self.date}'

    def mark_thanked(self, user):
        """Mark donation as thanked."""
        from django.utils import timezone
        self.thanked = True
        self.thanked_at = timezone.now()
        self.thanked_by = user
        self.save(update_fields=['thanked', 'thanked_at', 'thanked_by'])
