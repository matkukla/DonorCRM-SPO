"""
URL patterns for dashboard endpoints.
"""
from django.urls import path

from apps.dashboard.views import (
    DashboardView,
    GivingSummaryView,
    LateDonationsView,
    MarkEventsSeenView,
    MonthlyGiftsView,
    NeedsAttentionView,
    RecentGiftsView,
    SupportProgressView,
    ThankYouQueueView,
    UserDashboardLayoutView,
    WhatChangedView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("mark-seen/", MarkEventsSeenView.as_view(), name="mark-events-seen"),
    path("what-changed/", WhatChangedView.as_view(), name="what-changed"),
    path("needs-attention/", NeedsAttentionView.as_view(), name="needs-attention"),
    path("late-donations/", LateDonationsView.as_view(), name="late-donations"),
    path("thank-you-queue/", ThankYouQueueView.as_view(), name="thank-you-queue"),
    path("support-progress/", SupportProgressView.as_view(), name="support-progress"),
    path("recent-gifts/", RecentGiftsView.as_view(), name="recent-gifts"),
    path("giving-summary/", GivingSummaryView.as_view(), name="giving-summary"),
    path("monthly-gifts/", MonthlyGiftsView.as_view(), name="monthly-gifts"),
    path("user/<uuid:pk>/layout/", UserDashboardLayoutView.as_view(), name="user-dashboard-layout"),
]
