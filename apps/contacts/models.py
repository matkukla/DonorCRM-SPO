"""
Contact model for donor and prospect management.
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ContactStatus(models.TextChoices):
    """
    Status of a contact in the fundraising pipeline.
    """
    PROSPECT = 'prospect', 'Prospect'
    ASKED = 'asked', 'Asked'
    DONOR = 'donor', 'Donor'
    LAPSED = 'lapsed', 'Lapsed'
    DECLINED = 'declined', 'Declined'


class Contact(TimeStampedModel):
    """
    Represents a donor or prospect.
    Each contact is owned by a specific staff member.
    """
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='contacts',
        db_index=True,
        help_text='Staff member who owns this contact'
    )

    # Basic information
    first_name = models.CharField('first name', max_length=150)
    last_name = models.CharField('last name', max_length=150)
    email = models.EmailField('email', blank=True)
    phone = models.CharField('phone', max_length=20, blank=True)
    phone_secondary = models.CharField('secondary phone', max_length=20, blank=True)

    # Address
    street_address = models.CharField('street address', max_length=255, blank=True)
    city = models.CharField('city', max_length=100, blank=True)
    state = models.CharField('state', max_length=50, blank=True)
    postal_code = models.CharField('postal code', max_length=20, blank=True)
    country = models.CharField('country', max_length=100, default='USA')

    # Status tracking
    status = models.CharField(
        'status',
        max_length=20,
        choices=ContactStatus.choices,
        default=ContactStatus.PROSPECT,
        db_index=True
    )

    # Giving statistics (denormalized for performance)
    first_gift_date = models.DateField('first gift date', null=True, blank=True, db_index=True)
    last_gift_date = models.DateField('last gift date', null=True, blank=True, db_index=True)
    last_gift_amount = models.DecimalField(
        'last gift amount',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_given = models.DecimalField(
        'total given',
        max_digits=12,
        decimal_places=2,
        default=0
    )
    gift_count = models.PositiveIntegerField('gift count', default=0)

    # Thank-you tracking
    last_thanked_at = models.DateTimeField('last thanked', null=True, blank=True)
    needs_thank_you = models.BooleanField('needs thank you', default=False, db_index=True)

    # Notes
    notes = models.TextField('notes', blank=True)

    # Groups/tags (many-to-many)
    groups = models.ManyToManyField(
        'groups.Group',
        related_name='contacts',
        blank=True
    )

    class Meta:
        db_table = 'contacts'
        verbose_name = 'contact'
        verbose_name_plural = 'contacts'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['owner', 'last_gift_date']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['email']),
            models.Index(fields=['needs_thank_you']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'email'],
                name='unique_contact_email_per_owner',
                condition=~models.Q(email='')
            )
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def full_name(self):
        """Return the contact's full name."""
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [self.street_address, self.city, self.state, self.postal_code]
        return ', '.join(p for p in parts if p)

    @property
    def has_active_pledge(self):
        """Check if contact has an active pledge."""
        return self.pledges.filter(status='active').exists()

    @property
    def monthly_pledge_amount(self):
        """Get total monthly equivalent of active pledges."""
        active_pledges = self.pledges.filter(status='active')
        total = 0
        for pledge in active_pledges:
            total += pledge.monthly_equivalent
        return total

    def update_giving_stats(self):
        """
        Recalculate giving statistics from donations.
        Called when donations are added/modified.
        """
        donations = self.donations.all()
        agg = donations.aggregate(
            total=models.Sum('amount'),
            count=models.Count('id'),
            first=models.Min('date'),
            last=models.Max('date')
        )

        self.total_given = agg['total'] or 0
        self.gift_count = agg['count'] or 0
        self.first_gift_date = agg['first']
        self.last_gift_date = agg['last']

        if agg['last']:
            last_donation = donations.order_by('-date').first()
            self.last_gift_amount = last_donation.amount if last_donation else None

        # Update status based on giving history
        if self.gift_count > 0 and self.status == ContactStatus.PROSPECT:
            self.status = ContactStatus.DONOR

        self.save(update_fields=[
            'total_given', 'gift_count', 'first_gift_date',
            'last_gift_date', 'last_gift_amount', 'status'
        ])

    def mark_thanked(self):
        """Mark contact as thanked."""
        from django.utils import timezone
        self.needs_thank_you = False
        self.last_thanked_at = timezone.now()
        self.save(update_fields=['needs_thank_you', 'last_thanked_at'])
