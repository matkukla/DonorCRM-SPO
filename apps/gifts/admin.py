"""
Admin configuration for gift tracking models.
"""
from django.contrib import admin

from apps.gifts.models import (
    Gift,
    GiftCredit,
    RecurringGift,
    RecurringGiftCredit,
    Solicitor,
)


@admin.register(Solicitor)
class SolicitorAdmin(admin.ModelAdmin):
    """Admin configuration for Solicitor model."""
    list_display = ['normalized_name', 'user', 'external_solicitor_id', 'created_at']
    list_filter = ['user']
    search_fields = ['normalized_name', 'external_solicitor_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Gift)
class GiftAdmin(admin.ModelAdmin):
    """Admin configuration for Gift model."""
    list_display = ['id', 'donor_contact', 'amount_cents', 'gift_date', 'fund', 'external_gift_id', 'created_at']
    list_filter = ['fund']
    search_fields = ['external_gift_id', 'donor_contact__first_name', 'donor_contact__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'gift_date'


@admin.register(GiftCredit)
class GiftCreditAdmin(admin.ModelAdmin):
    """Admin configuration for GiftCredit model."""
    list_display = ['id', 'gift', 'solicitor', 'amount_cents', 'created_at']
    list_filter = ['solicitor']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(RecurringGift)
class RecurringGiftAdmin(admin.ModelAdmin):
    """Admin configuration for RecurringGift model."""
    list_display = ['id', 'donor_contact', 'amount_cents', 'frequency', 'status', 'start_date', 'created_at']
    list_filter = ['status', 'frequency', 'fund']
    search_fields = ['external_gift_id', 'donor_contact__first_name', 'donor_contact__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'


@admin.register(RecurringGiftCredit)
class RecurringGiftCreditAdmin(admin.ModelAdmin):
    """Admin configuration for RecurringGiftCredit model."""
    list_display = ['id', 'recurring_gift', 'solicitor', 'amount_cents', 'created_at']
    list_filter = ['solicitor']
    readonly_fields = ['id', 'created_at', 'updated_at']
