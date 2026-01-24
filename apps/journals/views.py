"""
Views for Journal management.
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response

from apps.core.permissions import IsOwnerOrAdmin
from apps.journals.models import Journal, JournalStageEvent
from apps.journals.serializers import (
    JournalCreateSerializer,
    JournalDetailSerializer,
    JournalListSerializer,
    JournalStageEventSerializer,
)


class JournalListCreateView(generics.ListCreateAPIView):
    """
    GET: List journals
    POST: Create a new journal
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'deadline', 'goal_amount']
    ordering = ['-created_at']
    filterset_fields = ['is_archived']

    @extend_schema(
        summary='List journals',
        description='Get all journals for the authenticated user (staff sees own, admin sees all)'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Create journal',
        description='Create a new journal with name, goal amount, and deadline'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        # Admin sees all journals
        if user.role == 'admin':
            queryset = Journal.objects.all()
        else:
            # Staff sees only their own journals
            queryset = Journal.objects.filter(owner=user)

        # Exclude archived by default unless is_archived filter present
        if 'is_archived' not in self.request.query_params:
            queryset = queryset.filter(is_archived=False)

        return queryset.select_related('owner')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JournalCreateSerializer
        return JournalListSerializer


class JournalDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve journal details
    PATCH/PUT: Update journal
    DELETE: Archive journal (soft delete)
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(
        summary='Get journal details',
        description='Retrieve full details for a specific journal'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Update journal',
        description='Update journal fields'
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary='Archive journal',
        description='Archive journal (soft delete)'
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Journal.objects.all().select_related('owner')
        return Journal.objects.filter(owner=user).select_related('owner')

    def get_serializer_class(self):
        return JournalDetailSerializer

    def destroy(self, request, *args, **kwargs):
        """Override destroy to implement soft-delete via archive()."""
        instance = self.get_object()
        instance.archive()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JournalStageEventListCreateView(generics.ListCreateAPIView):
    """
    GET: List stage events
    POST: Create a new stage event
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='List stage events',
        description='Get stage events, optionally filtered by journal_contact_id'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Create stage event',
        description='Create a new stage event for a journal contact'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        # Admin sees all stage events
        if user.role == 'admin':
            queryset = JournalStageEvent.objects.all()
        else:
            # Staff sees stage events for their own journals
            queryset = JournalStageEvent.objects.filter(
                journal_contact__journal__owner=user
            )

        # Filter by journal_contact_id if provided
        journal_contact_id = self.request.query_params.get('journal_contact_id')
        if journal_contact_id:
            queryset = queryset.filter(journal_contact_id=journal_contact_id)

        return queryset.select_related(
            'journal_contact',
            'journal_contact__journal',
            'journal_contact__contact',
            'triggered_by'
        ).order_by('-created_at')

    def get_serializer_class(self):
        return JournalStageEventSerializer
