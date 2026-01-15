"""
Admin configuration for Group model.
"""
from django.contrib import admin

from apps.groups.models import Group


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_system', 'contact_count', 'created_at')
    list_filter = ('is_system', 'owner')
    search_fields = ('name', 'description')
    ordering = ('name',)

    def contact_count(self, obj):
        return obj.contacts.count()
    contact_count.short_description = 'Contacts'
