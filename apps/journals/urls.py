"""
URL configuration for journals app.
"""
from django.urls import path

from apps.journals.views import (
    DecisionDetailView,
    DecisionHistoryListView,
    DecisionListCreateView,
    JournalContactDestroyView,
    JournalContactListCreateView,
    JournalDetailView,
    JournalListCreateView,
    JournalStageEventListCreateView,
    NextStepDetailView,
    NextStepListCreateView,
)

app_name = 'journals'

urlpatterns = [
    path('', JournalListCreateView.as_view(), name='journal-list'),
    path('<uuid:pk>/', JournalDetailView.as_view(), name='journal-detail'),
    path('stage-events/', JournalStageEventListCreateView.as_view(), name='stage-event-list'),
    path('journal-members/', JournalContactListCreateView.as_view(), name='journal-member-list'),
    path('journal-members/<uuid:pk>/', JournalContactDestroyView.as_view(), name='journal-member-detail'),
    path('decisions/', DecisionListCreateView.as_view(), name='decision-list'),
    path('decisions/<uuid:pk>/', DecisionDetailView.as_view(), name='decision-detail'),
    path('decision-history/', DecisionHistoryListView.as_view(), name='decision-history-list'),
    path('next-steps/', NextStepListCreateView.as_view(), name='nextstep-list'),
    path('next-steps/<uuid:pk>/', NextStepDetailView.as_view(), name='nextstep-detail'),
]
