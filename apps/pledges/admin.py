"""
Admin configuration for Pledge model.
"""
from django.contrib import admin

from apps.pledges.models import Pledge


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = (
        'contact', 'amount', 'frequency', 'status',
        'start_date', 'next_expected_date', 'is_late', 'days_late'
    )
    list_filter = ('status', 'frequency', 'is_late')
    search_fields = ('contact__first_name', 'contact__last_name')
    ordering = ('-created_at',)

    readonly_fields = (
        'last_fulfilled_date', 'next_expected_date',
        'total_expected', 'total_received',
        'is_late', 'days_late', 'late_notified_at',
        'created_at', 'updated_at'
    )
