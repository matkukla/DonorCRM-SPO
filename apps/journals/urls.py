"""
URL configuration for journals app.
"""
from django.urls import path

from apps.journals.views import (
    JournalDetailView,
    JournalListCreateView,
    JournalStageEventListCreateView,
)

app_name = 'journals'

urlpatterns = [
    path('', JournalListCreateView.as_view(), name='journal-list'),
    path('<uuid:pk>/', JournalDetailView.as_view(), name='journal-detail'),
    path('stage-events/', JournalStageEventListCreateView.as_view(), name='stage-event-list'),
]
