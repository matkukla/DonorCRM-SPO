"""
Admin configuration for import infrastructure models.
"""
from django.contrib import admin

from apps.imports.models import (
    Fund, ImportRun, ImportRowError, ImportBatch, ImportBatchType, ImportBatchStatus,
    MPDUpload, MPDSnapshot
)


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    """Admin configuration for Fund model."""
    list_display = ['name', 'external_id', 'status', 'owner', 'created_at']
    list_filter = ['status', 'owner']
    search_fields = ['name', 'external_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    """Admin configuration for ImportRun model."""
    list_display = [
        'id', 'type', 'status', 'filename', 'total_rows',
        'created_count', 'updated_count', 'error_count',
        'uploaded_by', 'created_at'
    ]
    list_filter = ['type', 'status', 'uploaded_by']
    search_fields = ['filename']
    readonly_fields = ['id', 'created_at', 'updated_at', 'error_summary']
    date_hierarchy = 'created_at'


@admin.register(ImportRowError)
class ImportRowErrorAdmin(admin.ModelAdmin):
    """Admin configuration for ImportRowError model."""
    list_display = ['id', 'import_run', 'row_number', 'created_at']
    list_filter = ['import_run__type']
    readonly_fields = ['id', 'created_at', 'updated_at', 'error_messages', 'row_data']


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    """Admin configuration for ImportBatch model."""
    list_display = [
        'id', 'import_type', 'status', 'filename',
        'total_rows', 'created_count', 'updated_count', 'error_count',
        'uploaded_by', 'created_at'
    ]
    list_filter = ['import_type', 'status', 'uploaded_by']
    search_fields = ['filename', 'sha256_hash']
    readonly_fields = ['id', 'created_at', 'updated_at', 'summary']
    date_hierarchy = 'created_at'


@admin.register(MPDUpload)
class MPDUploadAdmin(admin.ModelAdmin):
    """Admin configuration for MPDUpload model."""
    list_display = [
        'id', 'filename', 'file_format', 'status',
        'total_rows', 'matched_count', 'unmatched_count',
        'uploaded_by', 'created_at'
    ]
    list_filter = ['status', 'file_format', 'uploaded_by']
    search_fields = ['filename']
    readonly_fields = ['id', 'created_at', 'updated_at', 'unmatched_rows']
    date_hierarchy = 'created_at'


@admin.register(MPDSnapshot)
class MPDSnapshotAdmin(admin.ModelAdmin):
    """Admin configuration for MPDSnapshot model."""
    list_display = [
        'id', 'user', 'upload', 'active_recurring_gifts',
        'mpd_standard', 'met_mpd_standard', 'current_mpd_cap',
        'created_at'
    ]
    list_filter = ['met_mpd_standard', 'met_maximum', 'match_met']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
