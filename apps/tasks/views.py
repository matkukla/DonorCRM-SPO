"""
Views for Task management.
"""
from datetime import date, timedelta

from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from apps.core.permissions import IsOwnerOrAdmin, IsSupervisorWriteRestricted, get_visible_user_ids
from apps.core.utils import get_safe_int_param
from apps.tasks.filters import TaskFilterSet
from apps.tasks.models import Task, TaskStatus
from apps.tasks.serializers import TaskCreateSerializer, TaskSerializer


class TaskListCreateView(generics.ListCreateAPIView):
    """
    GET: List tasks
    POST: Create a new task
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["due_date", "priority", "created_at"]
    ordering = ["due_date", "-priority"]
    filterset_class = TaskFilterSet
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        visible = get_visible_user_ids(user, request=self.request)
        queryset = Task.objects.filter(owner_id__in=visible)

        return queryset.select_related("owner", "contact", "broadcast__sender")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TaskCreateSerializer
        return TaskSerializer


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve task details
    PATCH/PUT: Update task
    DELETE: Delete task
    """

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin, IsSupervisorWriteRestricted]

    def get_queryset(self):
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        return Task.objects.filter(owner_id__in=visible).select_related(
            "owner", "contact", "broadcast__sender"
        )

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        if (
            task.broadcast_id
            and str(task.owner_id) == str(request.user.id)
            and request.user.role == "missionary"
        ):
            return Response(
                {"detail": "Broadcast tasks cannot be edited by recipients."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if (
            task.broadcast_id
            and str(task.owner_id) == str(request.user.id)
            and request.user.role == "missionary"
        ):
            return Response(
                {"detail": "Broadcast tasks cannot be deleted by recipients."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


class TaskCompleteView(APIView):
    """
    POST: Mark task as completed
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        try:
            visible = get_visible_user_ids(user, request=request)
            task = Task.objects.get(pk=pk, owner_id__in=visible)
        except Task.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

        if task.status == TaskStatus.COMPLETED:
            return Response(
                {"detail": "Task is already completed."}, status=status.HTTP_400_BAD_REQUEST
            )

        task.mark_complete(user)
        return Response({"detail": "Task marked as completed."})


class OverdueTasksView(generics.ListAPIView):
    """
    GET: List overdue tasks
    """

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        today = date.today()

        base_query = Task.objects.filter(
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS], due_date__lt=today
        ).select_related("contact", "owner")

        visible = get_visible_user_ids(user, request=self.request)
        base_query = base_query.filter(owner_id__in=visible)
        return base_query


class UpcomingTasksView(generics.ListAPIView):
    """
    GET: List upcoming tasks (next 7 days)
    """

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        today = date.today()
        days = get_safe_int_param(self.request, "days", default=7, min_val=1, max_val=365)
        end_date = today + timedelta(days=days)

        base_query = Task.objects.filter(
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
            due_date__gte=today,
            due_date__lte=end_date,
        ).select_related("contact", "owner")

        visible = get_visible_user_ids(user, request=self.request)
        base_query = base_query.filter(owner_id__in=visible)
        return base_query
