"""
Base models for DonorCRM.
"""
import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model with UUID primary key and created/updated timestamps.
    All models in DonorCRM should inherit from this.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class OrgSettings(TimeStampedModel):
    """
    Singleton row holding org-level settings.

    annual_goal_cents: when set (>0), the admin's Fiscal Year Pace tile uses
    this number as the org's annual fundraising goal. When 0/null, the tile
    falls back to summing each missionary's monthly_support_goal_cents * 12.
    """

    annual_goal_cents = models.PositiveBigIntegerField(
        default=0,
        help_text=(
            "Org-wide annual fundraising goal in cents. 0 means use the sum "
            "of each missionary's monthly goal * 12 instead."
        ),
    )

    class Meta:
        db_table = "org_settings"
        verbose_name = "Org settings"
        verbose_name_plural = "Org settings"

    def __str__(self):
        return f"OrgSettings (annual_goal=${self.annual_goal_cents / 100:,.0f})"

    @classmethod
    def get_solo(cls):
        """Return the single OrgSettings row, creating it if missing."""
        instance, _ = cls.objects.get_or_create(pk=cls._solo_uuid())
        return instance

    @staticmethod
    def _solo_uuid():
        # Deterministic UUID so there is exactly one row.
        return uuid.UUID("00000000-0000-0000-0000-000000000001")

    def save(self, *args, **kwargs):
        # Belt-and-suspenders singleton enforcement: callers should use
        # OrgSettings.get_solo(), but if anyone instantiates the model
        # directly we coerce them onto the canonical UUID so we never end up
        # with two rows that say different things about the org-wide goal.
        self.pk = self._solo_uuid()
        super().save(*args, **kwargs)
