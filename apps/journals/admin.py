"""
Django admin configuration for journals app.
"""
from django.contrib import admin

from apps.journals.models import Journal, JournalContact, JournalStageEvent


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'goal_amount', 'deadline', 'is_archived', 'created_at']
    list_filter = ['is_archived', 'created_at']
    search_fields = ['name', 'owner__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(JournalContact)
class JournalContactAdmin(admin.ModelAdmin):
    list_display = ['journal', 'contact', 'created_at']
    list_filter = ['created_at']


@admin.register(JournalStageEvent)
class JournalStageEventAdmin(admin.ModelAdmin):
    list_display = ['journal_contact', 'stage', 'event_type', 'created_at']
    list_filter = ['stage', 'event_type', 'created_at']
