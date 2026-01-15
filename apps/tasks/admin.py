"""
Admin configuration for Task model.
"""
from django.contrib import admin

from apps.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'owner', 'contact', 'task_type',
        'priority', 'status', 'due_date', 'is_overdue'
    )
    list_filter = ('status', 'task_type', 'priority', 'due_date')
    search_fields = ('title', 'description', 'contact__first_name', 'contact__last_name')
    ordering = ('due_date', '-priority')

    readonly_fields = ('completed_at', 'completed_by', 'created_at', 'updated_at')

    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
