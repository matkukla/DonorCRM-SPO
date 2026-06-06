"""
Filters for FeedbackEntry list view.
"""

import django_filters

from apps.feedback.models import FeedbackEntry


class FeedbackEntryFilterSet(django_filters.FilterSet):
    """Filter set for FeedbackEntry. Uses individual DateFilter fields per
    the django-filter 24.3 constraint (DateFromToRangeFilter has breaking
    suffix changes in 25.x)."""

    type = django_filters.CharFilter(field_name="type")
    status = django_filters.CharFilter(field_name="status")
    submitter = django_filters.UUIDFilter(field_name="submitter_id")
    created_at__gte = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="gte",
    )
    created_at__lte = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    class Meta:
        model = FeedbackEntry
        fields = ["type", "status", "submitter"]
