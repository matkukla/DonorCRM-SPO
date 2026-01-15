"""
Admin configuration for Event model.
"""
from django.contrib import admin

from apps.events.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user', 'event_type', 'severity',
        'contact', 'is_read', 'is_new', 'created_at'
    )
    list_filter = ('event_type', 'severity', 'is_read', 'is_new', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    ordering = ('-created_at',)

    readonly_fields = ('created_at', 'read_at')
