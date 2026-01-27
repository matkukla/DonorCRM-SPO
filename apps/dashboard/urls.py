"""
URL patterns for dashboard endpoints.
"""
from django.urls import path

from apps.dashboard.views import (
    DashboardView,
    LateDonationsView,
    NeedsAttentionView,
    RecentGiftsView,
    RecentJournalActivityView,
    SupportProgressView,
    ThankYouQueueView,
    WhatChangedView,
)

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('what-changed/', WhatChangedView.as_view(), name='what-changed'),
    path('needs-attention/', NeedsAttentionView.as_view(), name='needs-attention'),
    path('late-donations/', LateDonationsView.as_view(), name='late-donations'),
    path('thank-you-queue/', ThankYouQueueView.as_view(), name='thank-you-queue'),
    path('support-progress/', SupportProgressView.as_view(), name='support-progress'),
    path('recent-gifts/', RecentGiftsView.as_view(), name='recent-gifts'),
    path('journal-activity/', RecentJournalActivityView.as_view(), name='journal-activity'),
]
