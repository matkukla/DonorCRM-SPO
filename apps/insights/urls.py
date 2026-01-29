"""
URL patterns for insights app.
"""
from django.urls import path

from apps.insights.views import (
    DonationsByMonthView,
    DonationsByYearView,
    FollowUpsView,
    LateDonationsView,
    MonthlyCommitmentsView,
    ReviewQueueView,
    TransactionsView,
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
]
