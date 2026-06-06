"""
Filters for PrayerIntention model.
"""

import django_filters

from apps.prayers.models import PrayerIntention


class PrayerIntentionFilterSet(django_filters.FilterSet):
    """Filter set for PrayerIntention model."""

    status = django_filters.CharFilter(field_name="status")
    owner = django_filters.NumberFilter(field_name="contact__owner_id")

    class Meta:
        model = PrayerIntention
        fields = ["status", "owner"]
