"""
URL patterns for tasks endpoints.
"""

from django.urls import path

from apps.tasks.broadcast_views import (
    BroadcastCancelView,
    BroadcastCopyListView,
    BroadcastDetailView,
    BroadcastListCreateView,
)
from apps.tasks.export_views import TaskExportCSVView
from apps.tasks.views import (
    OverdueTasksView,
    TaskCompleteView,
    TaskDetailView,
    TaskListCreateView,
    UpcomingTasksView,
)

app_name = "tasks"

urlpatterns = [
    path("", TaskListCreateView.as_view(), name="task-list"),
    path("export/csv/", TaskExportCSVView.as_view(), name="task-export-csv"),
    path("overdue/", OverdueTasksView.as_view(), name="task-overdue"),
    path("upcoming/", UpcomingTasksView.as_view(), name="task-upcoming"),
    # Broadcast URLs must come before <uuid:pk> to avoid UUID capture
    path("broadcasts/", BroadcastListCreateView.as_view(), name="broadcast-list"),
    path("broadcasts/<uuid:pk>/", BroadcastDetailView.as_view(), name="broadcast-detail"),
    path("broadcasts/<uuid:pk>/cancel/", BroadcastCancelView.as_view(), name="broadcast-cancel"),
    path("broadcasts/<uuid:pk>/copies/", BroadcastCopyListView.as_view(), name="broadcast-copies"),
    path("<uuid:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("<uuid:pk>/complete/", TaskCompleteView.as_view(), name="task-complete"),
]
