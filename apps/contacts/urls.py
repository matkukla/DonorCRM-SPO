"""
URL patterns for contacts endpoints.
"""
from django.urls import path

from apps.contacts.export_views import ContactExportCSVView
from apps.contacts.views import (
    ContactDetailView,
    ContactEmailsView,
    ContactGiftsView,
    ContactJournalEventsView,
    ContactJournalsView,
    ContactListCreateView,
    ContactPrayerIntentionsView,
    ContactRecurringGiftsView,
    ContactSearchView,
    ContactTasksView,
    ContactThankView,
    DismissDuplicateView,
    DuplicateCheckView,
    MergeContactsView,
)

app_name = "contacts"

urlpatterns = [
    path("", ContactListCreateView.as_view(), name="contact-list"),
    path("export/csv/", ContactExportCSVView.as_view(), name="contact-export-csv"),
    path("emails/", ContactEmailsView.as_view(), name="contact-emails"),
    path("search/", ContactSearchView.as_view(), name="contact-search"),
    path("duplicates/check/", DuplicateCheckView.as_view(), name="duplicate-check"),
    path("duplicates/merge/", MergeContactsView.as_view(), name="duplicate-merge"),
    path("duplicates/dismiss/", DismissDuplicateView.as_view(), name="duplicate-dismiss"),
    path("<uuid:pk>/", ContactDetailView.as_view(), name="contact-detail"),
    path("<uuid:pk>/thank/", ContactThankView.as_view(), name="contact-thank"),
    path("<uuid:pk>/donations/", ContactGiftsView.as_view(), name="contact-donations"),
    path("<uuid:pk>/pledges/", ContactRecurringGiftsView.as_view(), name="contact-pledges"),
    path("<uuid:pk>/tasks/", ContactTasksView.as_view(), name="contact-tasks"),
    path(
        "<uuid:pk>/prayer-intentions/",
        ContactPrayerIntentionsView.as_view(),
        name="contact-prayers",
    ),
    path("<uuid:pk>/journals/", ContactJournalsView.as_view(), name="contact-journals"),
    path(
        "<uuid:pk>/journal-events/",
        ContactJournalEventsView.as_view(),
        name="contact-journal-events",
    ),
]
