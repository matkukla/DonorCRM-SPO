"""
Models for prayer intention tracking.

Provides PrayerIntention model to track prayer requests per contact,
with M2M gift linkage for auto-creation from RE gift descriptions.
"""

from django.db import models

from apps.core.encryption import EncryptedTextField
from apps.core.models import TimeStampedModel


class PrayerIntentionStatus(models.TextChoices):
    """Status of a prayer intention."""

    ACTIVE = "active", "Active"
    ANSWERED = "answered", "Answered"
    ARCHIVED = "archived", "Archived"


class PrayerIntention(TimeStampedModel):
    """
    A prayer intention linked to a donor contact.

    Every prayer intention must be tied to a contact (not nullable).
    Links to one or more Gifts via M2M for auto-creation from RE descriptions.
    Multiple gifts from the same donor with the same prayer text share one
    PrayerIntention record.
    """

    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="prayer_intentions",
        db_index=True,
        help_text="Contact this prayer intention is for",
    )
    gifts = models.ManyToManyField(
        "gifts.Gift",
        blank=True,
        related_name="prayer_intentions",
        help_text="Gifts that triggered this prayer intention (if auto-created)",
    )
    title = models.CharField("title", max_length=255)
    # Encrypted at rest. Imports dedup via Python-side comparison over the
    # contact's existing intentions (apps.imports.*) — no blind index needed
    # because per-contact intention counts are tiny.
    description = EncryptedTextField("description", blank=True)
    status = models.CharField(
        "status",
        max_length=20,
        choices=PrayerIntentionStatus.choices,
        default=PrayerIntentionStatus.ACTIVE,
        db_index=True,
    )
    answered_at = models.DateTimeField(
        "answered at", null=True, blank=True, help_text="Timestamp when marked as answered"
    )
    archived_at = models.DateTimeField(
        "archived at", null=True, blank=True, help_text="Timestamp when archived"
    )
    last_prayed_at = models.DateTimeField(
        "last prayed at",
        null=True,
        blank=True,
        help_text="Timestamp of last prayer for this intention",
    )

    class Meta:
        db_table = "prayer_intentions"
        verbose_name = "prayer intention"
        verbose_name_plural = "prayer intentions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["contact", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.contact})"
