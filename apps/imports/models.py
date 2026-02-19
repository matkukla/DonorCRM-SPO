"""
Models for CSV import infrastructure.

Provides Fund, ImportRun, and ImportRowError models for tracking
CSV imports from SPO and other external systems.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class ImportType(models.TextChoices):
    """Types of CSV imports supported."""
    FUNDS = 'funds', 'Funds'
    ENTITIES = 'entities', 'Entities'
    TRANSACTIONS = 'transactions', 'Transactions'
    PLEDGES = 'pledges', 'Pledges'


class ImportStatus(models.TextChoices):
    """Import processing status."""
    PENDING = 'pending', 'Pending'
    VALIDATING = 'validating', 'Validating'
    VALIDATED = 'validated', 'Validated'
    IMPORTING = 'importing', 'Importing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Fund(TimeStampedModel):
    """
    Represents a fund/account/campaign from SPO.

    Funds are imported before transactions and referenced via external_id.
    Used for categorizing donations by account/campaign.
    """
    external_id = models.CharField(
        'external ID',
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Fund ID from SPO system'
    )
    name = models.CharField(
        'fund name',
        max_length=255
    )
    status = models.CharField(
        'status',
        max_length=20,
        default='active',
        help_text='active, inactive, or closed'
    )
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='funds',
        verbose_name='owner',
        help_text='Owner if fund is user-specific, null for org-wide funds'
    )

    class Meta:
        db_table = 'funds'
        verbose_name = 'fund'
        verbose_name_plural = 'funds'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.external_id})'


class ImportRun(TimeStampedModel):
    """
    Audit trail for each CSV import operation.

    Tracks status, counts, and errors for import history.
    Each import run has a type (funds, entities, etc.) and progresses
    through status states from pending to completed/failed.
    """
    type = models.CharField(
        'import type',
        max_length=20,
        choices=ImportType.choices,
        db_index=True
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=ImportStatus.choices,
        default=ImportStatus.PENDING
    )

    # File metadata
    filename = models.CharField(
        'filename',
        max_length=255
    )
    total_rows = models.IntegerField(
        'total rows',
        default=0
    )

    # Results
    created_count = models.IntegerField(
        'created count',
        default=0
    )
    updated_count = models.IntegerField(
        'updated count',
        default=0
    )
    skipped_count = models.IntegerField(
        'skipped count',
        default=0
    )
    error_count = models.IntegerField(
        'error count',
        default=0
    )

    # User tracking
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='import_runs',
        verbose_name='uploaded by'
    )

    # Error summary (first 20 errors for quick preview)
    error_summary = models.JSONField(
        'error summary',
        default=dict,
        blank=True,
        help_text='JSON dict with sample errors for preview'
    )

    class Meta:
        db_table = 'import_runs'
        verbose_name = 'import run'
        verbose_name_plural = 'import runs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-created_at']),
            models.Index(fields=['type', 'status']),
        ]

    def __str__(self):
        return f'{self.get_type_display()} import by {self.uploaded_by} on {self.created_at.date()}'


class ImportRowError(TimeStampedModel):
    """
    Individual row errors for failed import rows.

    Stores validation errors with line numbers for error reports.
    Enables "Download Errors CSV" feature for users to fix and re-upload.
    """
    import_run = models.ForeignKey(
        ImportRun,
        on_delete=models.CASCADE,
        related_name='row_errors',
        verbose_name='import run'
    )
    row_number = models.IntegerField(
        'row number'
    )
    error_messages = models.JSONField(
        'error messages',
        help_text='List of error strings for this row'
    )
    row_data = models.JSONField(
        'row data',
        help_text='Original CSV row as dict for error CSV download'
    )

    class Meta:
        db_table = 'import_row_errors'
        verbose_name = 'import row error'
        verbose_name_plural = 'import row errors'
        ordering = ['row_number']
        indexes = [
            models.Index(fields=['import_run', 'row_number']),
        ]

    def __str__(self):
        return f'Row {self.row_number}: {len(self.error_messages)} errors'


class MPDUpload(TimeStampedModel):
    """Audit trail for each Smartsheet MPD report upload."""
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='mpd_uploads',
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
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='processing',
    )
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'mpd_uploads'
        ordering = ['-created_at']

    def __str__(self):
        return f'MPD Upload by {self.uploaded_by} on {self.created_at.date()}'


class MPDSnapshot(TimeStampedModel):
    """Monthly MPD financial snapshot for a missionary (User)."""
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='mpd_snapshots',
    )
    upload = models.ForeignKey(
        MPDUpload,
        on_delete=models.CASCADE,
        related_name='snapshots',
    )

    # Financial fields (all nullable for partial data)
    active_recurring_gifts = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    annual_gifts = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    monthly_average = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    annual_mpd_estimate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mpd_standard = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_below_mpd_standard = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mpd_maximum = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_above_below_maximum = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    latest_roll_forward_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_mpd_cap = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    proj_monthly_deduction_rfb = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pay_forecast_12_months = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pay_forecast_over_fy = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_one_time_gifts_april = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Percentage field (stored as integer: 104 for "104%", -16 for "-16%")
    pct_standard_to_max = models.IntegerField(null=True, blank=True)

    # Boolean fields (Yes/No columns)
    met_mpd_standard = models.BooleanField(null=True)
    met_maximum = models.BooleanField(null=True)
    match_met = models.BooleanField(null=True)
    match_met_rest_fy = models.BooleanField(null=True)

    # Special field: can be numeric string or "infinite"
    months_remaining_rf = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        db_table = 'mpd_snapshots'
        ordering = ['-upload__created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'upload'],
                name='unique_snapshot_per_user_per_upload'
            ),
        ]
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'MPD Snapshot for {self.user} ({self.upload.created_at.date()})'
