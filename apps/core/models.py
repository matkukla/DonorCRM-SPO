"""
Base models for DonorCRM.
"""
import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model with UUID primary key and created/updated timestamps.
    All models in DonorCRM should inherit from this.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


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


class DataAccessLog(models.Model):
    """Append-only record of who accessed PII-bearing endpoints, when, and how.

    Populated by ``apps.core.access_log_middleware.DataAccessLogMiddleware``
    on every request whose URL matches a configured PII-touching pattern
    (contacts, gifts, exports). One row per request — exact resource IDs
    are recorded for retrieve endpoints; list endpoints record a count.

    Append-only at the application level: no Django admin write access,
    no API surface, no ``.update()`` / ``.delete()`` callers in app code.
    The ``purge_expired_data`` command is the only sanctioned deleter and
    only acts on rows past the retention window
    (see ``docs/security/data-retention.md``).

    For DB-level append-only enforcement (recommended for SOC 2-credible
    posture), grant the application's Postgres role only INSERT/SELECT on
    this table and run ``purge_expired_data`` under a separate role with
    DELETE. Provisioning runbook: ``docs/security/access-controls.md``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Authenticated user making the request. NULL for anonymous.",
    )
    # Stable internal ID for actor; persists even if the user is deleted, so
    # the audit trail survives right-to-erasure of the actor's account.
    actor_id_snapshot = models.UUIDField(null=True, blank=True, editable=False)

    # If admin/supervisor was viewing-as another user, the user being viewed.
    view_as_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # The HTTP request shape. Uses path + method rather than a logical "action"
    # name so middleware doesn't need a per-view registry.
    method = models.CharField(max_length=8, db_index=False)
    path = models.CharField(max_length=512, db_index=True)

    # The resource class name when identifiable from the URL pattern (e.g.
    # "Contact", "Gift"). NULL for paths that don't map to a single resource.
    resource_type = models.CharField(max_length=64, blank=True, default="")
    # Specific row ID for retrieve endpoints, NULL for list endpoints.
    resource_id = models.CharField(max_length=64, blank=True, default="")
    # For list endpoints, the row count returned (or 0 if unknown).
    row_count = models.PositiveIntegerField(default=0)

    # Network identifiers — IP and User-Agent for correlation. UA is
    # truncated to 256 chars to keep the row size bounded.
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True, default="")

    # Final HTTP status — useful for distinguishing "looked at it" from
    # "tried but got 403/404".
    status_code = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "core_dataaccesslog"
        verbose_name = "data access log"
        verbose_name_plural = "data access log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["actor", "-timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
            # actor_id_snapshot is the only stable identifier after the
            # actor FK is SET_NULL'd on user deletion. Index it so audit
            # queries about a deleted actor do not table-scan.
            models.Index(fields=["actor_id_snapshot"]),
        ]
        # No default permissions; do not register in admin.
        default_permissions = ()

    def __str__(self):
        return f"{self.timestamp.isoformat()} {self.method} {self.path}"
