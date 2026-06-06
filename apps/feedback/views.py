"""
Views for feedback API endpoints.
"""

from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter

from django_filters.rest_framework import DjangoFilterBackend

from apps.feedback.filters import FeedbackEntryFilterSet
from apps.feedback.models import FeedbackEntry
from apps.feedback.permissions import IsAdminOrCreateOnly
from apps.feedback.serializers import FeedbackEntryCreateSerializer, FeedbackEntrySerializer


class FeedbackListCreateView(generics.ListCreateAPIView):
    """
    POST: Submit a new feedback entry. Any authenticated user.
    GET: List all feedback entries. Admin only.
    """

    permission_classes = [IsAdminOrCreateOnly]
    throttle_scope = "feedback"
    filterset_class = FeedbackEntryFilterSet
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        "title",
        "description",
        "submitter__email",
        "submitter__first_name",
        "submitter__last_name",
    ]
    ordering_fields = ["created_at", "status", "type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return FeedbackEntry.objects.select_related("submitter").all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FeedbackEntryCreateSerializer
        return FeedbackEntrySerializer

    def perform_create(self, serializer):
        user_agent = self.request.META.get("HTTP_USER_AGENT", "")[:500]
        serializer.save(
            submitter=self.request.user,
            user_agent=user_agent,
        )


class FeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/PUT/DELETE on a single feedback entry. Admin only.
    Only `status` is writeable on update.
    """

    permission_classes = [IsAdminOrCreateOnly]
    serializer_class = FeedbackEntrySerializer

    def get_queryset(self):
        return FeedbackEntry.objects.select_related("submitter").all()
