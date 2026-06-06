"""
URL patterns for prayer intention endpoints.
"""

from django.urls import path

from apps.prayers.views import (
    MarkPrayedView,
    PrayerIntentionDetailView,
    PrayerIntentionListCreateView,
    TodaysFocusView,
)

app_name = "prayers"

urlpatterns = [
    path("", PrayerIntentionListCreateView.as_view(), name="prayer-list"),
    path("focus/", TodaysFocusView.as_view(), name="prayer-focus"),
    path("<uuid:pk>/", PrayerIntentionDetailView.as_view(), name="prayer-detail"),
    path("<uuid:pk>/prayed/", MarkPrayedView.as_view(), name="prayer-mark-prayed"),
]
