"""
URL patterns for donations endpoints.
"""
from django.urls import path

from apps.donations.views import (
    DonationByMonthView,
    DonationDetailView,
    DonationListCreateView,
    DonationSummaryView,
    DonationThankView,
)

app_name = 'donations'

urlpatterns = [
    path('', DonationListCreateView.as_view(), name='donation-list'),
    path('summary/', DonationSummaryView.as_view(), name='donation-summary'),
    path('by-month/', DonationByMonthView.as_view(), name='donation-by-month'),
    path('<uuid:pk>/', DonationDetailView.as_view(), name='donation-detail'),
    path('<uuid:pk>/thank/', DonationThankView.as_view(), name='donation-thank'),
]
