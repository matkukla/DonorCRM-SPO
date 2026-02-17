"""
URL patterns for tasks endpoints.
"""
from django.urls import path

from apps.tasks.export_views import TaskExportCSVView
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
    path('export/csv/', TaskExportCSVView.as_view(), name='task-export-csv'),
    path('overdue/', OverdueTasksView.as_view(), name='task-overdue'),
    path('upcoming/', UpcomingTasksView.as_view(), name='task-upcoming'),
    path('<uuid:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('<uuid:pk>/complete/', TaskCompleteView.as_view(), name='task-complete'),
]
