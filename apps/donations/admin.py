"""
Admin configuration for Donation model.
"""
from django.contrib import admin

from apps.donations.models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        'contact', 'amount', 'date', 'donation_type',
        'payment_method', 'thanked', 'import_batch'
    )
    list_filter = ('donation_type', 'payment_method', 'thanked', 'date')
    search_fields = ('contact__first_name', 'contact__last_name', 'external_id')
    ordering = ('-date',)
    date_hierarchy = 'date'

    readonly_fields = ('created_at', 'updated_at', 'thanked_at', 'thanked_by')
