"""
Admin configuration for User model.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""

    list_display = (
        'email', 'first_name', 'last_name', 'role',
        'is_active', 'is_staff', 'date_joined'
    )
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Role & Permissions', {
            'fields': ('role', 'monthly_goal', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Preferences', {'fields': ('email_notifications',)}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
        ('Groups', {'fields': ('groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'password1', 'password2',
                'role', 'is_active', 'is_staff'
            ),
        }),
    )
