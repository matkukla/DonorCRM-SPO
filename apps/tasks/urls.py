"""
URL patterns for tasks endpoints.
"""
from django.urls import path

from apps.tasks.views import (
    OverdueTasksView,
    TaskCompleteView,
    TaskDetailView,
    TaskListCreateView,
    UpcomingTasksView,
)

app_name = 'tasks'

urlpatterns = [
    path('', TaskListCreateView.as_view(), name='task-list'),
    path('overdue/', OverdueTasksView.as_view(), name='task-overdue'),
    path('upcoming/', UpcomingTasksView.as_view(), name='task-upcoming'),
    path('<uuid:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('<uuid:pk>/complete/', TaskCompleteView.as_view(), name='task-complete'),
]
