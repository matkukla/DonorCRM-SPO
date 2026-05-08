"""
Models for gift tracking with Raiser's Edge-compatible solicitor credit splitting.

Provides Solicitor, Gift, GiftCredit, RecurringGift, and RecurringGiftCredit
models to replace the existing Donation/Pledge system with cents-based amounts
and multi-solicitor credit attribution.
"""
from decimal import Decimal

from django.db import models

from apps.core.encryption import EncryptedTextField
from apps.core.models import TimeStampedModel

# ---------------------------------------------------------------------------
# TextChoices enums
# ---------------------------------------------------------------------------


class PaymentType(models.TextChoices):
    """Payment method for a gift."""

    CREDIT_CARD = "credit_card", "Credit Card"
    DIRECT_DEPOSIT = "direct_deposit", "Direct Deposit"
    CHECK = "check", "Check"
    CASH = "cash", "Cash"
    ONLINE = "online", "Online"


class RecurringGiftStatus(models.TextChoices):
    """Status of a recurring gift commitment."""

    ACTIVE = "active", "Active"
    HELD = "held", "Held"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    TERMINATED = "terminated", "Terminated"


class RecurringGiftFrequency(models.TextChoices):
    """Installment frequency for recurring gifts."""

    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    SEMI_ANNUALLY = "semi_annually", "Semi-Annually"
    ANNUALLY = "annually", "Annually"
    BIMONTHLY = "bimonthly", "Bimonthly"
    BIWEEKLY = "biweekly", "Biweekly"
    WEEKLY = "weekly", "Weekly"
    IRREGULAR = "irregular", "Irregular"


# ---------------------------------------------------------------------------
# Solicitor
# ---------------------------------------------------------------------------


class Solicitor(TimeStampedModel):
    """
    A fundraising solicitor who receives credit for gifts.

    May optionally link to a DonorCRM User account. External solicitor IDs
    from Raiser's Edge are stored for import matching.
    """

    normalized_name = models.CharField(
        "normalized name",
        max_length=255,
        db_index=True,
        help_text='Normalized "Last, First" for matching',
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitor_profile",
        help_text="Linked DonorCRM user account (auto-detected or manual)",
    )
    external_solicitor_id = models.CharField(
        "external solicitor ID",
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Solicitor ID from Raiser's Edge",
    )

    class Meta:
        db_table = "solicitors"
        verbose_name = "solicitor"
        verbose_name_plural = "solicitors"
        ordering = ["normalized_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_solicitor_id"],
                name="unique_external_solicitor_id",
                condition=~models.Q(external_solicitor_id=""),
            )
        ]

    def __str__(self):
        return self.normalized_name


# ---------------------------------------------------------------------------
# Gift
# ---------------------------------------------------------------------------


class Gift(TimeStampedModel):
    """
    Individual gift record linked to a donor contact.

    Replaces Donation model with cents-based amounts and solicitor credit
    support via GiftCredit junction table.
    """

    # Link to donor (required per user decision)
    donor_contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="gifts",
        db_index=True,
        help_text="Donor who made this gift",
    )

    # Link to fund
    fund = models.ForeignKey(
        "imports.Fund",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gifts",
        help_text="Fund/account this gift is attributed to",
    )

    # Link to source recurring gift (if this is a generated recurring payment)
    recurring_gift = models.ForeignKey(
        "gifts.RecurringGift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_gifts",
        help_text="Source recurring gift if this is a generated recurring payment",
    )

    # External ID for idempotent imports
    external_gift_id = models.CharField(
        "external gift ID",
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Gift ID from Raiser's Edge or external system",
    )

    # Gift details (cents-based)
    amount_cents = models.PositiveBigIntegerField(
        "amount (cents)", help_text="Gift amount in cents (e.g., 10000 = $100.00)"
    )
    gift_date = models.DateField("gift date", db_index=True)
    # Encrypted at rest; substring search via search_fields is no longer
    # supported (encrypted column).
    description = EncryptedTextField("description", blank=True)
    payment_type = models.CharField(
        "payment type",
        max_length=20,
        choices=PaymentType.choices,
        blank=True,
        help_text="Payment method: Credit Card, Direct Deposit, Check, Cash, or Online",
    )

    class Meta:
        db_table = "gifts"
        verbose_name = "gift"
        verbose_name_plural = "gifts"
        ordering = ["-gift_date", "-created_at"]
        indexes = [
            models.Index(fields=["donor_contact", "gift_date"]),
            models.Index(fields=["gift_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_gift_id"],
                name="unique_external_gift_id",
                condition=~models.Q(external_gift_id=""),
            )
        ]

    def __str__(self):
        return f"${self.amount_dollars:.2f} from {self.donor_contact} on {self.gift_date}"

    @property
    def amount_dollars(self):
        """Return amount as Decimal dollars for display."""
        return Decimal(self.amount_cents) / Decimal(100)


# ---------------------------------------------------------------------------
# GiftCredit
# ---------------------------------------------------------------------------


class GiftCredit(TimeStampedModel):
    """
    Links a Gift to a Solicitor with a per-credit amount.

    Enables split-credit attribution where a single gift can be credited
    to multiple solicitors with different amounts.
    """

    gift = models.ForeignKey(Gift, on_delete=models.CASCADE, related_name="credits", db_index=True)
    solicitor = models.ForeignKey(
        Solicitor, on_delete=models.PROTECT, related_name="gift_credits", db_index=True
    )
    amount_cents = models.PositiveBigIntegerField(
        "credit amount (cents)", help_text="Amount credited to this solicitor in cents"
    )

    class Meta:
        db_table = "gift_credits"
        verbose_name = "gift credit"
        verbose_name_plural = "gift credits"
        constraints = [
            models.UniqueConstraint(
                fields=["gift", "solicitor"], name="unique_gift_solicitor_credit"
            )
        ]

    def __str__(self):
        return f"${self.amount_dollars:.2f} credit to {self.solicitor} for {self.gift}"

    @property
    def amount_dollars(self):
        """Return amount as Decimal dollars for display."""
        return Decimal(self.amount_cents) / Decimal(100)


# ---------------------------------------------------------------------------
# RecurringGift
# ---------------------------------------------------------------------------


class RecurringGift(TimeStampedModel):
    """
    Recurring gift commitment from a donor.

    Replaces Pledge model with cents-based amounts, RE-compatible status
    and frequency values, and solicitor credit support via
    RecurringGiftCredit junction table.
    """

    # Link to donor (required per user decision)
    donor_contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="recurring_gifts",
        db_index=True,
        help_text="Donor who made this recurring gift commitment",
    )

    # Link to fund
    fund = models.ForeignKey(
        "imports.Fund",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_gifts",
        help_text="Fund/account this recurring gift is attributed to",
    )

    # External ID for idempotent imports
    external_gift_id = models.CharField(
        "external gift ID",
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Recurring gift ID from Raiser's Edge or external system",
    )

    # Installment details (cents-based, per-installment amount)
    amount_cents = models.PositiveBigIntegerField(
        "amount (cents)", help_text="Per-installment amount in cents (e.g., 10000 = $100.00)"
    )
    frequency = models.CharField("frequency", max_length=20, choices=RecurringGiftFrequency.choices)

    # Timeline
    start_date = models.DateField("start date", db_index=True)
    end_date = models.DateField("end date", null=True, blank=True)

    # Status tracking
    status = models.CharField(
        "status",
        max_length=20,
        choices=RecurringGiftStatus.choices,
        default=RecurringGiftStatus.ACTIVE,
        db_index=True,
    )

    # Encrypted at rest; substring search no longer supported.
    description = EncryptedTextField("description", blank=True)
    payment_type = models.CharField(
        "payment type",
        max_length=20,
        choices=PaymentType.choices,
        blank=True,
        help_text="Payment method: Credit Card, Direct Deposit, Check, Cash, or Online",
    )

    class Meta:
        db_table = "recurring_gifts"
        verbose_name = "recurring gift"
        verbose_name_plural = "recurring gifts"
        ordering = ["-start_date", "-created_at"]
        indexes = [
            models.Index(fields=["donor_contact", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_gift_id"],
                name="unique_recurring_external_gift_id",
                condition=~models.Q(external_gift_id=""),
            )
        ]

    def __str__(self):
        return f"${self.amount_dollars:.2f}/{self.frequency} from {self.donor_contact}"

    @property
    def amount_dollars(self):
        """Return amount as Decimal dollars for display."""
        return Decimal(self.amount_cents) / Decimal(100)

    @property
    def monthly_equivalent(self):
        """Calculate monthly equivalent amount for support progress calculations."""
        multipliers = {
            RecurringGiftFrequency.MONTHLY: Decimal("1"),
            RecurringGiftFrequency.QUARTERLY: Decimal("1") / Decimal("3"),
            RecurringGiftFrequency.SEMI_ANNUALLY: Decimal("1") / Decimal("6"),
            RecurringGiftFrequency.ANNUALLY: Decimal("1") / Decimal("12"),
            RecurringGiftFrequency.BIMONTHLY: Decimal("1") / Decimal("2"),
            RecurringGiftFrequency.BIWEEKLY: Decimal("26") / Decimal("12"),
            RecurringGiftFrequency.WEEKLY: Decimal("52") / Decimal("12"),
            RecurringGiftFrequency.IRREGULAR: Decimal("1"),
        }
        multiplier = multipliers.get(self.frequency, Decimal("1"))
        return round(self.amount_dollars * multiplier, 2)


# ---------------------------------------------------------------------------
# RecurringGiftCredit
# ---------------------------------------------------------------------------


class RecurringGiftCredit(TimeStampedModel):
    """
    Links a RecurringGift to a Solicitor with a per-credit amount.

    Same pattern as GiftCredit but for recurring gift commitments.
    """

    recurring_gift = models.ForeignKey(
        RecurringGift, on_delete=models.CASCADE, related_name="credits", db_index=True
    )
    solicitor = models.ForeignKey(
        Solicitor, on_delete=models.PROTECT, related_name="recurring_gift_credits", db_index=True
    )
    amount_cents = models.PositiveBigIntegerField(
        "credit amount (cents)", help_text="Amount credited to this solicitor in cents"
    )

    class Meta:
        db_table = "recurring_gift_credits"
        verbose_name = "recurring gift credit"
        verbose_name_plural = "recurring gift credits"
        constraints = [
            models.UniqueConstraint(
                fields=["recurring_gift", "solicitor"],
                name="unique_recurring_gift_solicitor_credit",
            )
        ]

    def __str__(self):
        return f"${self.amount_dollars:.2f} credit to {self.solicitor} for {self.recurring_gift}"

    @property
    def amount_dollars(self):
        """Return amount as Decimal dollars for display."""
        return Decimal(self.amount_cents) / Decimal(100)
