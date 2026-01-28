"""
URL patterns for contacts endpoints.
"""
from django.urls import path

from apps.contacts.views import (
    ContactDetailView,
    ContactDonationsView,
    ContactEmailsView,
    ContactJournalEventsView,
    ContactJournalsView,
    ContactListCreateView,
    ContactPledgesView,
    ContactSearchView,
    ContactTasksView,
    ContactThankView,
)

app_name = 'contacts'

urlpatterns = [
    path('', ContactListCreateView.as_view(), name='contact-list'),
    path('emails/', ContactEmailsView.as_view(), name='contact-emails'),
    path('search/', ContactSearchView.as_view(), name='contact-search'),
    path('<uuid:pk>/', ContactDetailView.as_view(), name='contact-detail'),
    path('<uuid:pk>/thank/', ContactThankView.as_view(), name='contact-thank'),
    path('<uuid:pk>/donations/', ContactDonationsView.as_view(), name='contact-donations'),
    path('<uuid:pk>/pledges/', ContactPledgesView.as_view(), name='contact-pledges'),
    path('<uuid:pk>/tasks/', ContactTasksView.as_view(), name='contact-tasks'),
    path('<uuid:pk>/journals/', ContactJournalsView.as_view(), name='contact-journals'),
    path('<uuid:pk>/journal-events/', ContactJournalEventsView.as_view(), name='contact-journal-events'),
]
