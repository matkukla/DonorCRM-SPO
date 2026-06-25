"""
FilterSet for Contact list filtering.
"""

from django.db.models import Q

import django_filters

from apps.contacts.models import Contact


class ContactFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    needs_thank_you = django_filters.BooleanFilter(field_name="needs_thank_you")
    last_gift_after = django_filters.DateFilter(field_name="last_gift_date", lookup_expr="gte")
    last_gift_before = django_filters.DateFilter(field_name="last_gift_date", lookup_expr="lte")
    group = django_filters.UUIDFilter(field_name="groups__id")
    # "Not contacted recently": last logged call/meeting before this datetime,
    # OR never contacted (null last_contacted). Requires the queryset to be
    # annotated with `last_contacted` (see apps/contacts/last_contacted.py).
    last_contacted_before = django_filters.IsoDateTimeFilter(method="filter_last_contacted_before")

    class Meta:
        model = Contact
        fields = ["status", "needs_thank_you", "last_gift_after", "last_gift_before", "group"]

    def filter_last_contacted_before(self, queryset, name, value):
        # Never-contacted donors (null) are the most neglected and must be
        # included in the "not contacted recently" set, not filtered out.
        return queryset.filter(Q(last_contacted__lt=value) | Q(last_contacted__isnull=True))
