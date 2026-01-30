"""
Admin configuration for import infrastructure models.
"""
from django.contrib import admin

from apps.imports.models import Fund, ImportRun, ImportRowError


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
