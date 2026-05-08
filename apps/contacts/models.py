"""
Contact model for donor and prospect management.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.blind_index import BinaryHashField, hash_value, normalize_phone
from apps.core.encryption import EncryptedTextField
from apps.core.models import TimeStampedModel


class ActiveContactManager(models.Manager):
    """Returns only non-merged contacts."""

    def get_queryset(self):
        return super().get_queryset().filter(is_merged=False)


class ContactStatus(models.TextChoices):
    """
    Status of a contact in the fundraising pipeline.
    """

    PROSPECT = "prospect", "Potential Donor"
    ASKED = "asked", "Asked"
    DONOR = "donor", "Donor"
    LAPSED = "lapsed", "Lapsed"
    DECLINED = "declined", "Declined"


class Contact(TimeStampedModel):
    """
    Represents a donor or prospect.
    Each contact is owned by a specific staff member.
    """

    objects = models.Manager()
    active = ActiveContactManager()

    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="contacts",
        db_index=True,
        help_text="Staff member who owns this contact",
    )

    # External ID for idempotent imports
    external_id = models.CharField(
        "external ID",
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Entity ID from external system (e.g., SPO)",
    )

    # External ID for RE constituent imports
    external_constituent_id = models.CharField(
        "external constituent ID",
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Constituent ID from Raiser's Edge",
    )

    # Organization name for organization constituents
    organization_name = models.CharField(
        "organization name",
        max_length=255,
        blank=True,
        help_text="Organization name (for organization-type constituents)",
    )

    # Basic information
    first_name = models.CharField("first name", max_length=150, blank=True)
    last_name = models.CharField("last name", max_length=150, blank=True)
    # email is encrypted at rest; equality lookups go through email_hash.
    # See apps.core.blind_index. Substring search is no longer supported.
    email = EncryptedTextField("email", blank=True)
    # HMAC-SHA256 of the normalized email. Synced from email in save().
    # The named index lives in Meta.indexes (`models.Index(fields=["email_hash"])`);
    # we deliberately do NOT set db_index=True here to avoid Postgres
    # maintaining a duplicate auto-generated B-tree on the same column.
    # nullable so empty-email rows have NULL (preserving the original
    # conditional unique constraint semantics).
    email_hash = BinaryHashField("email hash", null=True, blank=True, editable=False)
    # phone and phone_secondary are encrypted at rest; equality dedup goes
    # through phone_hash / phone_secondary_hash. Substring search is no
    # longer supported on either column.
    phone = EncryptedTextField("phone", blank=True)
    phone_hash = BinaryHashField("phone hash", null=True, blank=True, editable=False, db_index=True)
    phone_secondary = EncryptedTextField("secondary phone", blank=True)
    phone_secondary_hash = BinaryHashField(
        "phone secondary hash", null=True, blank=True, editable=False, db_index=True
    )

    # Address — street_address is encrypted at rest. City/state/postal/country
    # remain plaintext; they are coarse-grained and not directly identifying.
    street_address = EncryptedTextField("street address", blank=True)
    city = models.CharField("city", max_length=100, blank=True)
    state = models.CharField("state", max_length=50, blank=True)
    postal_code = models.CharField("postal code", max_length=20, blank=True)
    country = models.CharField("country", max_length=100, default="USA")

    # Status tracking
    status = models.CharField(
        "status",
        max_length=20,
        choices=ContactStatus.choices,
        default=ContactStatus.PROSPECT,
        db_index=True,
    )

    # Giving statistics (denormalized for performance)
    first_gift_date = models.DateField("first gift date", null=True, blank=True, db_index=True)
    last_gift_date = models.DateField("last gift date", null=True, blank=True, db_index=True)
    last_gift_amount = models.DecimalField(
        "last gift amount", max_digits=10, decimal_places=2, null=True, blank=True
    )
    total_given = models.DecimalField("total given", max_digits=12, decimal_places=2, default=0)
    gift_count = models.PositiveIntegerField("gift count", default=0)

    # Thank-you tracking
    last_thanked_at = models.DateTimeField("last thanked", null=True, blank=True)
    needs_thank_you = models.BooleanField("needs thank you", default=False, db_index=True)

    # Notes — encrypted at rest. Round-trips as plaintext via the descriptor.
    # Legacy plaintext rows continue to read until the data migration completes.
    notes = EncryptedTextField("notes", blank=True)

    # Merge tracking
    is_merged = models.BooleanField("merged", default=False, db_index=True)
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="merged_contacts",
        help_text="Contact this was merged into",
    )

    # Groups/tags (many-to-many)
    groups = models.ManyToManyField("groups.Group", related_name="contacts", blank=True)

    class Meta:
        db_table = "contacts"
        verbose_name = "contact"
        verbose_name_plural = "contacts"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "last_gift_date"]),
            models.Index(fields=["last_name", "first_name"]),
            # email plaintext is encrypted; equality lookups use email_hash
            models.Index(fields=["email_hash"]),
            models.Index(fields=["needs_thank_you"]),
            models.Index(fields=["owner", "is_merged"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "email_hash"],
                name="unique_contact_email_per_owner",
                condition=models.Q(email_hash__isnull=False) & models.Q(is_merged=False),
            ),
            models.UniqueConstraint(
                fields=["owner", "external_id"],
                name="unique_contact_external_id_per_owner",
                condition=~models.Q(external_id="") & models.Q(is_merged=False),
            ),
            models.UniqueConstraint(
                fields=["external_constituent_id"],
                name="unique_external_constituent_id",
                condition=~models.Q(external_constituent_id="") & models.Q(is_merged=False),
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        # Keep blind-index hashes in sync with their plaintext sources on
        # every save() path. bulk_update / .update() bypass this; data
        # migrations and rotate_pii_encryption compute hashes explicitly.
        self.email_hash = hash_value(self.email)
        self.phone_hash = hash_value(normalize_phone(self.phone))
        self.phone_secondary_hash = hash_value(normalize_phone(self.phone_secondary))
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Return the contact's full name, falling back to organization_name for org contacts."""
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.organization_name

    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [self.street_address, self.city, self.state, self.postal_code]
        return ", ".join(p for p in parts if p)

    @property
    def has_active_recurring_gift(self):
        """Check if contact has an active recurring gift."""
        return self.recurring_gifts.filter(status="active").exists()

    @property
    def has_active_pledge(self):
        """Alias for has_active_recurring_gift (backward compatibility during transition)."""
        return self.has_active_recurring_gift

    @property
    def monthly_recurring_gift_amount(self):
        """Get total monthly equivalent of active recurring gifts."""
        active_recurring = self.recurring_gifts.filter(status="active")
        total = 0
        for rg in active_recurring:
            total += rg.monthly_equivalent
        return total

    @property
    def monthly_pledge_amount(self):
        """Alias for monthly_recurring_gift_amount (backward compatibility during transition)."""
        return self.monthly_recurring_gift_amount

    def update_giving_stats(self):
        """Recalculate giving statistics from gifts.

        Called when gifts are added/modified. Concurrent calls for the
        same contact are serialized via a row-level write lock; the
        ``SELECT ... FOR UPDATE`` statement queues subsequent callers
        until the enclosing transaction commits.
        """
        from django.db import transaction

        with transaction.atomic():
            # Acquire the row-level write lock and rebind to the locked
            # instance so any later mutation goes through the row that
            # was actually locked. The aggregate below reads from the
            # gifts table, not from ``self``, so this is mostly belt-
            # and-suspenders, but it makes the lock contract explicit
            # and avoids a stale ``self`` field surprising future code.
            locked = Contact.objects.select_for_update().get(pk=self.pk)

            gifts = locked.gifts.all()
            agg = gifts.aggregate(
                total_cents=models.Sum("amount_cents"),
                count=models.Count("id"),
                first=models.Min("gift_date"),
                last=models.Max("gift_date"),
            )

            locked.total_given = Decimal(agg["total_cents"] or 0) / Decimal(100)
            locked.gift_count = agg["count"] or 0
            locked.first_gift_date = agg["first"]
            locked.last_gift_date = agg["last"]

            if agg["last"]:
                last_gift = gifts.order_by("-gift_date").first()
                locked.last_gift_amount = last_gift.amount_dollars if last_gift else None
            else:
                locked.last_gift_amount = None

            # Update status based on giving history
            if locked.gift_count > 0 and locked.status == ContactStatus.PROSPECT:
                locked.status = ContactStatus.DONOR

            locked.save(
                update_fields=[
                    "total_given",
                    "gift_count",
                    "first_gift_date",
                    "last_gift_date",
                    "last_gift_amount",
                    "status",
                ]
            )

            # Mirror the recomputed values back onto ``self`` so callers
            # that hold the original instance see the new state without
            # a refresh_from_db.
            for f in (
                "total_given",
                "gift_count",
                "first_gift_date",
                "last_gift_date",
                "last_gift_amount",
                "status",
            ):
                setattr(self, f, getattr(locked, f))

    def mark_thanked(self):
        """Mark contact as thanked."""
        from django.utils import timezone

        self.needs_thank_you = False
        self.last_thanked_at = timezone.now()
        self.save(update_fields=["needs_thank_you", "last_thanked_at"])


class DismissedDuplicate(TimeStampedModel):
    """Tracks dismissed duplicate pairs so they are not re-flagged."""

    contact_a = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="+")
    contact_b = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="+")
    dismissed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dismissed_duplicates"
    )

    class Meta:
        db_table = "dismissed_duplicates"
        constraints = [
            models.UniqueConstraint(fields=["contact_a", "contact_b"], name="unique_dismissed_pair")
        ]

    def save(self, **kwargs):
        # Canonicalize: contact_a_id < contact_b_id (string comparison of UUIDs)
        if str(self.contact_a_id) > str(self.contact_b_id):
            self.contact_a_id, self.contact_b_id = self.contact_b_id, self.contact_a_id
        super().save(**kwargs)


class ContactMergeLog(TimeStampedModel):
    """Audit trail for contact merge operations."""

    survivor = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, related_name="merge_logs_as_survivor"
    )
    loser_id = models.UUIDField(help_text="ID of the merged-away contact")
    loser_name = models.CharField(max_length=300, help_text="Name snapshot at merge time")
    merged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="merge_logs"
    )
    field_overrides = models.JSONField(
        default=dict, help_text="Fields auto-filled from merged contact"
    )
    records_migrated = models.JSONField(default=dict, help_text="Counts of migrated FK records")

    class Meta:
        db_table = "contact_merge_logs"
        ordering = ["-created_at"]
