"""
URL patterns for events endpoints.
"""
from django.urls import path

from apps.events.views import (
    EventDetailView,
    EventListView,
    EventMarkAllReadView,
    EventMarkReadView,
    UnreadEventCountView,
)

app_name = 'events'

urlpatterns = [
    path('', EventListView.as_view(), name='event-list'),
    path('unread-count/', UnreadEventCountView.as_view(), name='event-unread-count'),
    path('read-all/', EventMarkAllReadView.as_view(), name='event-read-all'),
    path('<uuid:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('<uuid:pk>/read/', EventMarkReadView.as_view(), name='event-read'),
]
