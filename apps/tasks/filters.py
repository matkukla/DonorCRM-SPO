"""
FilterSet for Task list filtering.
"""
import django_filters

from apps.tasks.models import Task


class TaskFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    task_type = django_filters.CharFilter(field_name="task_type")
    priority = django_filters.CharFilter(field_name="priority")
    due_date_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_date_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    contact = django_filters.UUIDFilter(field_name="contact_id")
    owner = django_filters.NumberFilter(field_name="owner_id")

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
        ]
