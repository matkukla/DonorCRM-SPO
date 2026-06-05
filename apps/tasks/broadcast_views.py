"""Views for Broadcast Task management."""
from django.db.models import Count, Q

from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from apps.tasks.broadcast_serializers import (
    BroadcastCreateSerializer,
    BroadcastTaskDetailSerializer,
    BroadcastTaskListSerializer,
    BroadcastUpdateSerializer,
)
from apps.tasks.broadcast_services import cancel_broadcast, create_broadcast, update_broadcast
from apps.tasks.models import BroadcastTask, Task, TaskStatus
from apps.tasks.serializers import TaskSerializer


def _broadcast_queryset_for_user(user):
    """Return annotated BroadcastTask queryset filtered by user role.

    Admin sees all broadcasts. Supervisor sees only broadcasts they sent.
    All other roles get an empty queryset.
    """
    if user.role == "admin":
        qs = BroadcastTask.objects.all()
    elif user.role == "supervisor":
        qs = BroadcastTask.objects.filter(sender=user)
    else:
        qs = BroadcastTask.objects.none()

    return qs.annotate(
        completed_count=Count(
            "copies",
            filter=Q(copies__status=TaskStatus.COMPLETED),
        ),
        total_count=Count("copies"),
    ).select_related("sender")


class BroadcastListCreateView(generics.ListCreateAPIView):
    """
    GET: List broadcasts (admin sees all, supervisor sees own).
    POST: Create a broadcast (admin/supervisor only).
    """

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "due_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _broadcast_queryset_for_user(self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BroadcastCreateSerializer
        return BroadcastTaskListSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "supervisor"):
            return Response(
                {"detail": "Only admins and supervisors can create broadcasts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BroadcastCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        broadcast = create_broadcast(
            sender=request.user,
            **serializer.validated_data,
        )

        # Re-query with annotations for the response
        annotated = _broadcast_queryset_for_user(request.user).get(pk=broadcast.pk)
        response_serializer = BroadcastTaskListSerializer(annotated, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class BroadcastDetailView(generics.RetrieveUpdateAPIView):
    """
    GET: Retrieve broadcast detail (includes recipient_ids).
    PATCH/PUT: Update broadcast (cascades to incomplete copies).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BroadcastTaskDetailSerializer

    def get_queryset(self):
        return _broadcast_queryset_for_user(self.request.user)

    def update(self, request, *args, **kwargs):
        broadcast = self.get_object()

        # Only sender or admin can update
        if request.user.role != "admin" and broadcast.sender_id != request.user.id:
            return Response(
                {"detail": "Only the broadcast sender or an admin can update."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BroadcastUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_broadcast(broadcast, **serializer.validated_data)

        # Re-query with annotations
        annotated = self.get_queryset().get(pk=broadcast.pk)
        serializer = BroadcastTaskDetailSerializer(annotated, context={"request": request})
        return Response(serializer.data)


class BroadcastCancelView(APIView):
    """POST: Cancel a broadcast (deletes incomplete copies, keeps completed)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        qs = _broadcast_queryset_for_user(request.user)
        try:
            broadcast = qs.get(pk=pk)
        except BroadcastTask.DoesNotExist:
            return Response(
                {"detail": "Broadcast not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only sender or admin can cancel
        if request.user.role != "admin" and broadcast.sender_id != request.user.id:
            return Response(
                {"detail": "Only the broadcast sender or an admin can cancel."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if broadcast.is_cancelled:
            return Response(
                {"detail": "Broadcast is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cancel_broadcast(broadcast)
        return Response({"detail": "Broadcast cancelled."})


class BroadcastCopyListView(generics.ListAPIView):
    """GET: List per-user task copies for a broadcast."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering = ["owner__first_name"]

    def get_queryset(self):
        qs = _broadcast_queryset_for_user(self.request.user)
        try:
            qs.get(pk=self.kwargs["pk"])
        except BroadcastTask.DoesNotExist:
            return Task.objects.none()

        return Task.objects.filter(broadcast_id=self.kwargs["pk"]).select_related(
            "owner", "contact", "broadcast__sender"
        )
