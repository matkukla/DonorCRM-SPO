"""FilterSet for Journal list filtering."""
import django_filters

from apps.journals.models import Journal


class JournalFilterSet(django_filters.FilterSet):
    deadline_after = django_filters.DateFilter(field_name='deadline', lookup_expr='gte')
    deadline_before = django_filters.DateFilter(field_name='deadline', lookup_expr='lte')

    class Meta:
        model = Journal
        fields = ['deadline_after', 'deadline_before']
        # NOTE: is_archived is handled in get_queryset(), NOT here — preserves archived-by-default behavior
