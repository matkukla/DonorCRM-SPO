"""
Filters for Gift and RecurringGift models.
"""
import django_filters

from apps.gifts.models import Gift, RecurringGift


class GiftFilterSet(django_filters.FilterSet):
    """Filter set for Gift model."""

    donor_contact = django_filters.UUIDFilter(field_name="donor_contact")
    fund = django_filters.UUIDFilter(field_name="fund")
    gift_date_after = django_filters.DateFilter(field_name="gift_date", lookup_expr="gte")
    gift_date_before = django_filters.DateFilter(field_name="gift_date", lookup_expr="lte")
    min_amount = django_filters.NumberFilter(method="filter_min_amount")
    max_amount = django_filters.NumberFilter(method="filter_max_amount")
    payment_type = django_filters.CharFilter(field_name="payment_type")
    owner = django_filters.NumberFilter(field_name="donor_contact__owner")
    is_recurring = django_filters.BooleanFilter(method="filter_is_recurring")

    class Meta:
        model = Gift
        fields = [
            "donor_contact",
            "fund",
            "gift_date_after",
            "gift_date_before",
            "min_amount",
            "max_amount",
            "payment_type",
            "owner",
            "is_recurring",
        ]

    def filter_is_recurring(self, queryset, name, value):
        if value is True:
            return queryset.filter(recurring_gift__isnull=False)
        elif value is False:
            return queryset.filter(recurring_gift__isnull=True)
        return queryset

    def filter_min_amount(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(amount_cents__gte=round(value * 100))

    def filter_max_amount(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(amount_cents__lte=round(value * 100))


class RecurringGiftFilterSet(django_filters.FilterSet):
    """Filter set for RecurringGift model."""

    donor_contact = django_filters.UUIDFilter(field_name="donor_contact")
    fund = django_filters.UUIDFilter(field_name="fund")
    status = django_filters.CharFilter(field_name="status")
    frequency = django_filters.CharFilter(field_name="frequency")
    owner = django_filters.NumberFilter(field_name="donor_contact__owner")

    class Meta:
        model = RecurringGift
        fields = ["donor_contact", "fund", "status", "frequency", "owner"]
