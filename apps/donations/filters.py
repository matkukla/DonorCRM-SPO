"""
FilterSet for Donation list filtering.
"""
import django_filters

from apps.donations.models import Donation


class DonationFilterSet(django_filters.FilterSet):
    donation_type = django_filters.CharFilter(field_name='donation_type')
    payment_method = django_filters.CharFilter(field_name='payment_method')
    thanked = django_filters.BooleanFilter(field_name='thanked')
    date_after = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_before = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    contact = django_filters.UUIDFilter(field_name='contact_id')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    fund = django_filters.UUIDFilter(field_name='fund_id')

    class Meta:
        model = Donation
        fields = ['donation_type', 'payment_method', 'thanked', 'date_after', 'date_before', 'contact', 'amount_min', 'amount_max', 'fund']
