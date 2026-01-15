"""
Admin configuration for Contact model.
"""
from django.contrib import admin

from apps.contacts.models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'email', 'owner', 'status',
        'total_given', 'gift_count', 'last_gift_date', 'needs_thank_you'
    )
    list_filter = ('status', 'owner', 'needs_thank_you', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    ordering = ('last_name', 'first_name')
    readonly_fields = (
        'total_given', 'gift_count', 'first_gift_date',
        'last_gift_date', 'last_gift_amount', 'created_at', 'updated_at'
    )

    fieldsets = (
        (None, {
            'fields': ('owner', 'first_name', 'last_name', 'status')
        }),
        ('Contact Info', {
            'fields': ('email', 'phone', 'phone_secondary')
        }),
        ('Address', {
            'fields': ('street_address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Giving Statistics', {
            'fields': (
                'total_given', 'gift_count', 'first_gift_date',
                'last_gift_date', 'last_gift_amount'
            )
        }),
        ('Thank You', {
            'fields': ('needs_thank_you', 'last_thanked_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'
