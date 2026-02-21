"""
Filters for Gift and RecurringGift models.
"""
import django_filters

from apps.gifts.models import Gift, RecurringGift


class GiftFilterSet(django_filters.FilterSet):
    """Filter set for Gift model."""
    donor_contact = django_filters.UUIDFilter(field_name='donor_contact')
    fund = django_filters.UUIDFilter(field_name='fund')
    gift_date_after = django_filters.DateFilter(field_name='gift_date', lookup_expr='gte')
    gift_date_before = django_filters.DateFilter(field_name='gift_date', lookup_expr='lte')
    min_amount = django_filters.NumberFilter(field_name='amount_cents', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount_cents', lookup_expr='lte')

    class Meta:
        model = Gift
        fields = ['donor_contact', 'fund', 'gift_date_after', 'gift_date_before', 'min_amount', 'max_amount']


class RecurringGiftFilterSet(django_filters.FilterSet):
    """Filter set for RecurringGift model."""
    donor_contact = django_filters.UUIDFilter(field_name='donor_contact')
    fund = django_filters.UUIDFilter(field_name='fund')
    status = django_filters.CharFilter(field_name='status')
    frequency = django_filters.CharFilter(field_name='frequency')

    class Meta:
        model = RecurringGift
        fields = ['donor_contact', 'fund', 'status', 'frequency']
