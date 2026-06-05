"""
Models for CSV import infrastructure.

Provides Fund, ImportRun, and ImportRowError models for tracking
CSV imports from SPO and other external systems.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class ImportType(models.TextChoices):
    """Types of CSV imports supported."""

    FUNDS = "funds", "Funds"
    ENTITIES = "entities", "Entities"
    TRANSACTIONS = "transactions", "Transactions"
    PLEDGES = "pledges", "Pledges"


class ImportStatus(models.TextChoices):
    """Import processing status."""

    PENDING = "pending", "Pending"
    VALIDATING = "validating", "Validating"
    VALIDATED = "validated", "Validated"
    IMPORTING = "importing", "Importing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Fund(TimeStampedModel):
    """
    Represents a fund/account/campaign from SPO.

    Funds are imported before transactions and referenced via external_id.
    Used for categorizing donations by account/campaign.
    """

    external_id = models.CharField(
        "external ID",
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Fund ID from SPO system",
    )
    name = models.CharField("fund name", max_length=255)
    status = models.CharField(
        "status", max_length=20, default="active", help_text="active, inactive, or closed"
    )
    owner = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="funds",
        verbose_name="owner",
        help_text="Owner if fund is user-specific, null for org-wide funds",
    )

    class Meta:
        db_table = "funds"
        verbose_name = "fund"
        verbose_name_plural = "funds"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.external_id})"


class ImportRun(TimeStampedModel):
    """
    Audit trail for each CSV import operation.

    Tracks status, counts, and errors for import history.
    Each import run has a type (funds, entities, etc.) and progresses
    through status states from pending to completed/failed.
    """

    type = models.CharField("import type", max_length=20, choices=ImportType.choices, db_index=True)
    status = models.CharField(
        "status", max_length=20, choices=ImportStatus.choices, default=ImportStatus.PENDING
    )

    # File metadata
    filename = models.CharField("filename", max_length=255)
    total_rows = models.IntegerField("total rows", default=0)

    # Results
    created_count = models.IntegerField("created count", default=0)
    updated_count = models.IntegerField("updated count", default=0)
    skipped_count = models.IntegerField("skipped count", default=0)
    error_count = models.IntegerField("error count", default=0)

    # User tracking
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="import_runs",
        verbose_name="uploaded by",
    )

    # Error summary (first 20 errors for quick preview)
    error_summary = models.JSONField(
        "error summary",
        default=dict,
        blank=True,
        help_text="JSON dict with sample errors for preview",
    )

    class Meta:
        db_table = "import_runs"
        verbose_name = "import run"
        verbose_name_plural = "import runs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["uploaded_by", "-created_at"]),
            models.Index(fields=["type", "status"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()} import by {self.uploaded_by} on {self.created_at.date()}"


class ImportRowError(TimeStampedModel):
    """
    Individual row errors for failed import rows.

    Stores validation errors with line numbers for error reports.
    Enables "Download Errors CSV" feature for users to fix and re-upload.
    """

    import_run = models.ForeignKey(
        ImportRun, on_delete=models.CASCADE, related_name="row_errors", verbose_name="import run"
    )
    row_number = models.IntegerField("row number")
    error_messages = models.JSONField(
        "error messages", help_text="List of error strings for this row"
    )
    row_data = models.JSONField(
        "row data", help_text="Original CSV row as dict for error CSV download"
    )

    class Meta:
        db_table = "import_row_errors"
        verbose_name = "import row error"
        verbose_name_plural = "import row errors"
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["import_run", "row_number"]),
        ]

    def __str__(self):
        return f"Row {self.row_number}: {len(self.error_messages)} errors"


class ImportBatchType(models.TextChoices):
    """Types of import batches for RE and generic imports."""

    RE_CONSTITUENT = "re_constituent", "RE Constituent"
    RE_SOLICITOR = "re_solicitor", "RE Solicitor"
    RE_GIFT = "re_gift", "RE Gift"
    RE_RECURRING_GIFT = "re_recurring_gift", "RE Recurring Gift"
    GENERIC_CONTACTS = "generic_contacts", "Generic Contacts"
    GENERIC_DONATIONS = "generic_donations", "Generic Donations"
    SMARTSHEET_MPD = "smartsheet_mpd", "Smartsheet MPD"
    SPO_MISSIONARY = "spo_missionary", "SPO Missionary Reconciliation"
    SPO_GIFT = "spo_gift", "SPO Gift Import"
    SPO_PRAYER = "spo_prayer", "SPO Prayer Import"


class ImportBatchStatus(models.TextChoices):
    """Processing status of an import batch."""

    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    DUPLICATE = "duplicate", "Duplicate (already processed)"


class ImportBatch(TimeStampedModel):
    """
    Universal import tracking model with SHA256 file dedup.

    Tracks all import types (RE, generic CSV, Smartsheet) with status,
    row counts, and a SHA256 hash unique per import type to prevent
    duplicate file processing.
    """

    import_type = models.CharField(
        "import type", max_length=30, choices=ImportBatchType.choices, db_index=True
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=ImportBatchStatus.choices,
        default=ImportBatchStatus.PENDING,
    )
    filename = models.CharField("filename", max_length=255)
    sha256_hash = models.CharField(
        "SHA256 hash",
        max_length=64,
        db_index=True,
        help_text="SHA256 hex digest for duplicate detection",
    )

    # Row counts
    total_rows = models.PositiveIntegerField("total rows", default=0)
    created_count = models.PositiveIntegerField("created count", default=0)
    updated_count = models.PositiveIntegerField("updated count", default=0)
    skipped_count = models.PositiveIntegerField("skipped count", default=0)
    error_count = models.PositiveIntegerField("error count", default=0)

    # Type-specific metadata
    summary = models.JSONField(
        "summary", default=dict, blank=True, help_text="Type-specific import metadata and results"
    )

    # User tracking
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="import_batches",
        verbose_name="uploaded by",
    )

    class Meta:
        db_table = "import_batches"
        verbose_name = "import batch"
        verbose_name_plural = "import batches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["uploaded_by", "-created_at"]),
            models.Index(fields=["import_type", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["import_type", "sha256_hash"], name="unique_import_batch_hash_per_type"
            )
        ]

    def __str__(self):
        return f"{self.get_import_type_display()} by {self.uploaded_by} ({self.status})"


class MPDUpload(TimeStampedModel):
    """Audit trail for each Smartsheet MPD report upload."""

    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="mpd_uploads",
    )
    filename = models.CharField(max_length=255)
    file_format = models.CharField(max_length=10)  # 'csv' or 'xlsx'

    # Row counts
    total_rows = models.IntegerField(default=0)
    matched_count = models.IntegerField(default=0)
    unmatched_count = models.IntegerField(default=0)

    # Unmatched row details stored as JSON list of {row, first_name, last_name}
    unmatched_rows = models.JSONField(default=list, blank=True)

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=[
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="processing",
    )
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "mpd_uploads"
        ordering = ["-created_at"]

    def __str__(self):
        return f"MPD Upload by {self.uploaded_by} on {self.created_at.date()}"


class MPDSnapshot(TimeStampedModel):
    """Monthly MPD financial snapshot for a missionary (User)."""

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="mpd_snapshots",
    )
    upload = models.ForeignKey(
        MPDUpload,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )

    # Financial fields (all nullable for partial data)
    active_recurring_gifts = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    annual_gifts = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    monthly_average = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    annual_mpd_estimate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    mpd_standard = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_below_mpd_standard = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    mpd_maximum = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_above_below_maximum = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    latest_roll_forward_balance = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    current_mpd_cap = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    proj_monthly_deduction_rfb = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    pay_forecast_12_months = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    pay_forecast_over_fy = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    total_one_time_gifts_april = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    # Percentage field (stored as integer: 104 for "104%", -16 for "-16%")
    pct_standard_to_max = models.IntegerField(null=True, blank=True)

    # Boolean fields (Yes/No columns)
    met_mpd_standard = models.BooleanField(null=True)
    met_maximum = models.BooleanField(null=True)
    match_met = models.BooleanField(null=True)
    match_met_rest_fy = models.BooleanField(null=True)

    # Special field: can be numeric string or "infinite"
    months_remaining_rf = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "mpd_snapshots"
        ordering = ["-upload__created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "upload"], name="unique_snapshot_per_user_per_upload"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"MPD Snapshot for {self.user} ({self.upload.created_at.date()})"


class MissionaryAlias(TimeStampedModel):
    """
    Maps ambiguous SPO source name variants to known missionary Users.

    Drives the three-level matching logic in the SPO reconciliation pipeline:
      1. Exact full name match
      2. Normalized (punctuation-stripped lowercase) match
      3. Alias table lookup (this model)

    user=None means an admin has seen this name and marked it as unresolved —
    distinct from "never seen before". This prevents repeated auto-create attempts
    for known-unresolvable names.
    """

    source_name = models.CharField(
        "source name",
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Name as it appears in SPO CSV export",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="name_aliases",
        null=True,
        blank=True,
        help_text="Resolved missionary. Null = unresolved.",
    )
    notes = models.TextField(blank=True, help_text="Optional admin notes")

    class Meta:
        db_table = "missionary_aliases"
        verbose_name = "missionary alias"
        verbose_name_plural = "missionary aliases"

    def __str__(self):
        return f"{self.source_name} -> {self.user}"
