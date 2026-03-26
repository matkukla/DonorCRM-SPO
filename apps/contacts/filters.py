"""
FilterSet for Contact list filtering.
"""
import django_filters

from apps.contacts.models import Contact


class ContactFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    needs_thank_you = django_filters.BooleanFilter(field_name='needs_thank_you')
    last_gift_after = django_filters.DateFilter(field_name='last_gift_date', lookup_expr='gte')
    last_gift_before = django_filters.DateFilter(field_name='last_gift_date', lookup_expr='lte')
    group = django_filters.UUIDFilter(field_name='groups__id')

    class Meta:
        model = Contact
        fields = ['status', 'needs_thank_you', 'last_gift_after', 'last_gift_before', 'group']
