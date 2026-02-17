"""
FilterSet for Pledge list filtering.
"""
import django_filters

from apps.pledges.models import Pledge


class PledgeFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    frequency = django_filters.CharFilter(field_name='frequency')
    is_late = django_filters.BooleanFilter(field_name='is_late')
    start_date_after = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')
    contact = django_filters.UUIDFilter(field_name='contact_id')

    class Meta:
        model = Pledge
        fields = ['status', 'frequency', 'is_late', 'start_date_after', 'start_date_before', 'contact']
