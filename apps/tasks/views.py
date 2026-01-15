"""
Views for Task management.
"""
from datetime import date, timedelta

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOwnerOrAdmin
from apps.tasks.models import Task, TaskStatus
from apps.tasks.serializers import TaskCreateSerializer, TaskSerializer


class TaskListCreateView(generics.ListCreateAPIView):
    """
    GET: List tasks
    POST: Create a new task
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']
    ordering = ['due_date', '-priority']
    filterset_fields = ['status', 'task_type', 'priority']
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin can see all tasks
        if user.role == 'admin':
            queryset = Task.objects.all()
        else:
            # Others see only their own tasks
            queryset = Task.objects.filter(owner=user)

        # Contact filter
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)

        return queryset.select_related('owner', 'contact')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskSerializer


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve task details
    PATCH/PUT: Update task
    DELETE: Delete task
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Task.objects.all()
        return Task.objects.filter(owner=user)


class TaskCompleteView(APIView):
    """
    POST: Mark task as completed
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        try:
            if user.role == 'admin':
                task = Task.objects.get(pk=pk)
            else:
                task = Task.objects.get(pk=pk, owner=user)
        except Task.DoesNotExist:
            return Response(
                {'detail': 'Task not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if task.status == TaskStatus.COMPLETED:
            return Response(
                {'detail': 'Task is already completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task.mark_complete(user)
        return Response({'detail': 'Task marked as completed.'})


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
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
            due_date__lt=today
        )

        if user.role == 'admin':
            return base_query
        return base_query.filter(owner=user)


class UpcomingTasksView(generics.ListAPIView):
    """
    GET: List upcoming tasks (next 7 days)
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        today = date.today()
        days = int(self.request.query_params.get('days', 7))
        end_date = today + timedelta(days=days)

        base_query = Task.objects.filter(
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
            due_date__gte=today,
            due_date__lte=end_date
        )

        if user.role == 'admin':
            return base_query
        return base_query.filter(owner=user)
