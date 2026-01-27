"""
Views for Journal management.
"""
from collections import defaultdict

from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import TruncMonth
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.core.permissions import IsOwnerOrAdmin
from apps.journals.models import (
    Decision,
    DecisionHistory,
    Journal,
    JournalContact,
    JournalStageEvent,
    NextStep,
    PipelineStage,
)
from apps.journals.serializers import (
    DecisionHistorySerializer,
    DecisionSerializer,
    JournalContactSerializer,
    JournalCreateSerializer,
    JournalDetailSerializer,
    JournalListSerializer,
    JournalStageEventSerializer,
    NextStepSerializer,
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


class JournalContactListCreateView(generics.ListCreateAPIView):
    """
    GET: List journal contact memberships with search/filter
    POST: Create a new journal contact membership
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JournalContactSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['contact__first_name', 'contact__last_name', 'contact__email']
    filterset_fields = ['contact__status']
    ordering_fields = ['created_at', 'contact__first_name', 'contact__last_name']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user

        # Base queryset with optimized joins
        queryset = JournalContact.objects.select_related('journal', 'contact')

        # Admin sees all, staff sees only their own journals
        if user.role != 'admin':
            queryset = queryset.filter(journal__owner=user)

        # Always exclude archived journals
        queryset = queryset.filter(journal__is_archived=False)

        # Filter by journal_id if provided
        journal_id = self.request.query_params.get('journal_id')
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override create to handle duplicate membership constraint with atomic transaction.
        """
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            # Handle unique constraint violation for duplicate journal+contact
            if 'unique' in str(e).lower():
                return Response(
                    {'detail': 'Contact already in this journal'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Re-raise non-unique integrity errors
            raise


class JournalContactDestroyView(generics.DestroyAPIView):
    """
    DELETE: Remove a contact from a journal
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JournalContactSerializer

    def get_queryset(self):
        user = self.request.user

        # Base queryset with optimized joins
        queryset = JournalContact.objects.select_related('journal', 'contact')

        # Admin sees all, staff sees only their own journals
        if user.role != 'admin':
            queryset = queryset.filter(journal__owner=user)

        return queryset

    @transaction.atomic
    def perform_destroy(self, instance):
        """Delete with atomic transaction."""
        instance.delete()


class DecisionHistoryPagination(PageNumberPagination):
    """Pagination for decision history list."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class DecisionListCreateView(generics.ListCreateAPIView):
    """
    GET: List decisions
    POST: Create a new decision
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DecisionSerializer

    def get_queryset(self):
        user = self.request.user

        # Base queryset with optimized joins
        queryset = Decision.objects.select_related(
            'journal_contact',
            'journal_contact__journal',
            'journal_contact__contact'
        )

        # Admin sees all, staff sees only their own journals
        if user.role != 'admin':
            queryset = queryset.filter(journal_contact__journal__owner=user)

        # Filter by journal_contact_id if provided
        journal_contact_id = self.request.query_params.get('journal_contact_id')
        if journal_contact_id:
            queryset = queryset.filter(journal_contact_id=journal_contact_id)

        # Filter by journal_id if provided
        journal_id = self.request.query_params.get('journal_id')
        if journal_id:
            queryset = queryset.filter(journal_contact__journal_id=journal_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override create to handle duplicate decision constraint with atomic transaction.
        """
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            # Handle unique constraint violation for duplicate journal_contact
            if 'unique' in str(e).lower():
                return Response(
                    {'detail': 'A decision already exists for this contact in this journal.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Re-raise non-unique integrity errors
            raise


class DecisionDetailView(generics.RetrieveUpdateAPIView):
    """
    GET: Retrieve decision details
    PATCH/PUT: Update decision (creates history record)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DecisionSerializer

    def get_queryset(self):
        user = self.request.user

        # Base queryset with optimized joins
        queryset = Decision.objects.select_related(
            'journal_contact',
            'journal_contact__journal',
            'journal_contact__contact'
        )

        # Admin sees all, staff sees only their own journals
        if user.role != 'admin':
            queryset = queryset.filter(journal_contact__journal__owner=user)

        return queryset


class DecisionHistoryListView(generics.ListAPIView):
    """
    GET: List decision history with pagination
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DecisionHistorySerializer
    pagination_class = DecisionHistoryPagination

    def get_queryset(self):
        user = self.request.user

        # Base queryset with optimized joins
        queryset = DecisionHistory.objects.select_related(
            'decision',
            'decision__journal_contact',
            'decision__journal_contact__journal',
            'changed_by'
        )

        # Admin sees all, staff sees only their own journals
        if user.role != 'admin':
            queryset = queryset.filter(decision__journal_contact__journal__owner=user)

        # Filter by decision_id if provided
        decision_id = self.request.query_params.get('decision_id')
        if decision_id:
            queryset = queryset.filter(decision_id=decision_id)

        # Filter by journal_contact_id if provided
        journal_contact_id = self.request.query_params.get('journal_contact_id')
        if journal_contact_id:
            queryset = queryset.filter(decision__journal_contact_id=journal_contact_id)

        return queryset.order_by('-created_at')


class NextStepListCreateView(generics.ListCreateAPIView):
    """
    GET: List next steps
    POST: Create a new next step
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NextStepSerializer

    def get_queryset(self):
        """Filter to next steps in journals owned by user (or all for admin)."""
        user = self.request.user

        if user.role == 'admin':
            qs = NextStep.objects.all()
        else:
            qs = NextStep.objects.filter(journal_contact__journal__owner=user)

        # Filter by journal_contact
        journal_contact_id = self.request.query_params.get('journal_contact')
        if journal_contact_id:
            qs = qs.filter(journal_contact_id=journal_contact_id)

        # Filter by completed status
        completed = self.request.query_params.get('completed')
        if completed is not None:
            qs = qs.filter(completed=completed.lower() == 'true')

        return qs.select_related('journal_contact__journal', 'journal_contact__contact')


class NextStepDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve next step details
    PATCH/PUT: Update next step (mark complete, edit, etc.)
    DELETE: Remove next step
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NextStepSerializer

    def get_queryset(self):
        """Filter to next steps in journals owned by user (or all for admin)."""
        user = self.request.user

        if user.role == 'admin':
            qs = NextStep.objects.all()
        else:
            qs = NextStep.objects.filter(journal_contact__journal__owner=user)

        return qs.select_related('journal_contact__journal', 'journal_contact__contact')


class JournalAnalyticsViewSet(viewsets.ViewSet):
    """
    Analytics endpoints for journal reporting.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _is_admin(self, request):
        return request.user.role == 'admin'

    @action(detail=False, methods=['get'], url_path='decision-trends')
    def decision_trends(self, request):
        """Decision counts over time (bar chart data)."""
        qs = Decision.objects.all() if self._is_admin(request) else Decision.objects.filter(
            journal_contact__journal__owner=request.user
        )
        trends = qs.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        return Response([
            {'month': item['month'].strftime('%Y-%m'), 'count': item['count']}
            for item in trends
        ])

    @action(detail=False, methods=['get'], url_path='stage-activity')
    def stage_activity(self, request):
        """Event counts by stage over time (multi-line chart data)."""
        qs = JournalStageEvent.objects.all() if self._is_admin(request) else JournalStageEvent.objects.filter(
            journal_contact__journal__owner=request.user
        )
        activity = qs.annotate(
            month=TruncMonth('created_at')
        ).values('month', 'stage').annotate(
            count=Count('id')
        ).order_by('month', 'stage')

        # Pivot data so each month has all stage counts
        by_month = defaultdict(lambda: {
            'contact': 0, 'meet': 0, 'close': 0,
            'decision': 0, 'thank': 0, 'next_steps': 0
        })

        for item in activity:
            month_str = item['month'].strftime('%Y-%m')
            by_month[month_str][item['stage']] = item['count']

        return Response([
            {'date': month, **counts}
            for month, counts in sorted(by_month.items())
        ])

    @action(detail=False, methods=['get'], url_path='pipeline-breakdown')
    def pipeline_breakdown(self, request):
        """Contacts by current pipeline stage (pie chart data)."""
        # Subquery to get most recent stage per journal_contact
        latest_stage = JournalStageEvent.objects.filter(
            journal_contact=OuterRef('pk')
        ).order_by('-created_at').values('stage')[:1]

        jc_qs = JournalContact.objects.all() if self._is_admin(request) else JournalContact.objects.filter(
            journal__owner=request.user
        )
        breakdown = jc_qs.annotate(
            current_stage=Subquery(latest_stage)
        ).values('current_stage').annotate(
            count=Count('id')
        ).order_by('current_stage')

        return Response([
            {'stage': item['current_stage'] or 'contact', 'count': item['count']}
            for item in breakdown
        ])

    @action(detail=False, methods=['get'], url_path='next-steps-queue')
    def next_steps_queue(self, request):
        """Upcoming next steps across all contacts (list data)."""
        from django.db.models import F

        ns_qs = NextStep.objects.all() if self._is_admin(request) else NextStep.objects.filter(
            journal_contact__journal__owner=request.user
        )
        steps = ns_qs.filter(
            completed=False
        ).select_related(
            'journal_contact__contact',
            'journal_contact__journal'
        ).order_by(
            F('due_date').asc(nulls_last=True),
            'created_at'
        )[:20]

        return Response([
            {
                'id': str(step.id),
                'title': step.title,
                'due_date': step.due_date.isoformat() if step.due_date else None,
                'contact_name': step.journal_contact.contact.full_name,
                'journal_name': step.journal_contact.journal.name,
                'journal_contact_id': str(step.journal_contact.id),
            }
            for step in steps
        ])

    @action(detail=False, methods=['get'], url_path='admin-summary')
    def admin_summary(self, request):
        """Cross-missionary aggregation data (admin only)."""
        # Check if user is staff
        if not request.user.is_staff:
            return Response(
                {'detail': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Aggregate across ALL journals (no owner filter)
        total_journals = Journal.objects.filter(is_archived=False).count()
        total_decisions = Decision.objects.count()

        # Journals by user
        journals_by_user = Journal.objects.filter(
            is_archived=False
        ).values(
            'owner__email'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        return Response({
            'total_journals': total_journals,
            'total_decisions': total_decisions,
            'journals_by_user': [
                {'email': item['owner__email'], 'count': item['count']}
                for item in journals_by_user
            ]
        })
