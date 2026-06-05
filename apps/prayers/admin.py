"""
Admin configuration for prayer intention models.
"""
from django.contrib import admin

from apps.prayers.models import PrayerIntention


@admin.register(PrayerIntention)
class PrayerIntentionAdmin(admin.ModelAdmin):
    """Admin configuration for PrayerIntention model."""

    list_display = ["id", "title", "contact", "status", "answered_at", "archived_at", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "contact__first_name", "contact__last_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
