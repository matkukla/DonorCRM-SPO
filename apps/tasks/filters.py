"""
FilterSet for Task list filtering.
"""

import django_filters

from apps.tasks.models import Task, TaskStatus


class TaskFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    task_type = django_filters.CharFilter(field_name="task_type")
    priority = django_filters.CharFilter(field_name="priority")
    due_date_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_date_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    contact = django_filters.UUIDFilter(field_name="contact_id")
    owner = django_filters.NumberFilter(field_name="owner_id")
    # ``?completed=false`` returns active (non-completed) tasks; ``?completed=true``
    # returns only completed tasks. Lets the Tasks tab (issue #168) split the list
    # into an active section and a separate "Completed Tasks" section without a
    # client-side filter that would break server-side pagination counts.
    completed = django_filters.BooleanFilter(method="filter_completed")

    def filter_completed(self, queryset, name, value):
        if value is True:
            return queryset.filter(status=TaskStatus.COMPLETED)
        if value is False:
            return queryset.exclude(status=TaskStatus.COMPLETED)
        return queryset

    class Meta:
        model = Task
        fields = [
            "status",
            "task_type",
            "priority",
            "due_date_after",
            "due_date_before",
            "contact",
            "owner",
            "completed",
        ]
