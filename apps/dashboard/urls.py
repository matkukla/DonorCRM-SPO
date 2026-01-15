"""
URL patterns for dashboard endpoints.
"""
from django.urls import path

from apps.dashboard.views import (
    AtRiskView,
    DashboardView,
    NeedsAttentionView,
    RecentGiftsView,
    SupportProgressView,
    ThankYouQueueView,
    WhatChangedView,
)

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('what-changed/', WhatChangedView.as_view(), name='what-changed'),
    path('needs-attention/', NeedsAttentionView.as_view(), name='needs-attention'),
    path('at-risk/', AtRiskView.as_view(), name='at-risk'),
    path('thank-you-queue/', ThankYouQueueView.as_view(), name='thank-you-queue'),
    path('support-progress/', SupportProgressView.as_view(), name='support-progress'),
    path('recent-gifts/', RecentGiftsView.as_view(), name='recent-gifts'),
]
