"""
URL patterns for insights app.
"""
from django.urls import path

from apps.insights.views import (
    ConversionFunnelView,
    DashboardOverviewView,
    DonationsByMonthView,
    DonationsByYearView,
    FollowUpsView,
    LateDonationsView,
    MonthlyCommitmentsView,
    ReviewQueueView,
    StalledContactsView,
    TeamActivityView,
    TeamTrendsView,
    TransactionsView,
    UserPerformanceView,
    UserTrendsView,
    UserJournalsView,
    StageContactsView,
    UserDrilldownView,
)

app_name = 'insights'

urlpatterns = [
    path('donations-by-month/', DonationsByMonthView.as_view(), name='donations-by-month'),
    path('donations-by-year/', DonationsByYearView.as_view(), name='donations-by-year'),
    path('monthly-commitments/', MonthlyCommitmentsView.as_view(), name='monthly-commitments'),
    path('late-donations/', LateDonationsView.as_view(), name='late-donations'),
    path('follow-ups/', FollowUpsView.as_view(), name='follow-ups'),
    path('review-queue/', ReviewQueueView.as_view(), name='review-queue'),
    path('transactions/', TransactionsView.as_view(), name='transactions'),

    # Admin analytics endpoints (Phase 13)
    path('admin/dashboard-overview/', DashboardOverviewView.as_view(), name='admin-dashboard-overview'),
    path('admin/stalled-contacts/', StalledContactsView.as_view(), name='admin-stalled-contacts'),
    path('admin/user-performance/', UserPerformanceView.as_view(), name='admin-user-performance'),
    path('admin/conversion-funnel/', ConversionFunnelView.as_view(), name='admin-conversion-funnel'),
    path('admin/team-activity/', TeamActivityView.as_view(), name='admin-team-activity'),
    path('admin/team-trends/', TeamTrendsView.as_view(), name='admin-team-trends'),
    path('admin/user-trends/', UserTrendsView.as_view(), name='admin-user-trends'),
    path('admin/user-journals/', UserJournalsView.as_view(), name='admin-user-journals'),
    path('admin/stage-contacts/', StageContactsView.as_view(), name='admin-stage-contacts'),
    path('admin/user-drilldown/', UserDrilldownView.as_view(), name='admin-user-drilldown'),
]
