"""
Views for Contact management.
"""
from django.db.models import Q, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import filters, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contacts.filters import ContactFilterSet
from apps.contacts.models import Contact, ContactStatus, DismissedDuplicate
from apps.contacts.serializers import (
    ContactCreateSerializer,
    ContactDetailSerializer,
    ContactListSerializer,
    ContactJournalMembershipSerializer,
    DuplicateCheckSerializer,
    DuplicateMatchSerializer,
    MergeRequestSerializer,
    DismissRequestSerializer,
)
from apps.contacts.services import find_duplicates_for_contact, merge_contacts
from apps.core.pagination import StandardPagination
from apps.core.permissions import (
    IsContactOwnerOrReadAccess,
    IsStaffOrAbove,
    IsSupervisorWriteRestricted,
    get_visible_user_ids,
)
from apps.journals.models import JournalContact, JournalStageEvent


@extend_schema_view(
    get=extend_schema(
        tags=['contacts'],
        summary='List contacts',
        description='List contacts owned by the current user. Admins can see all contacts.',
        parameters=[
            OpenApiParameter(name='status', description='Filter by contact status', type=str),
            OpenApiParameter(name='needs_thank_you', description='Filter by thank-you status', type=bool),
            OpenApiParameter(name='group', description='Filter by group ID', type=str),
            OpenApiParameter(name='owner', description='Filter by owner ID (admin only)', type=str),
            OpenApiParameter(name='search', description='Search in name and email', type=str),
        ]
    ),
    post=extend_schema(
        tags=['contacts'],
        summary='Create contact',
        description='Create a new contact. The contact will be owned by the current user.'
    )
)
class ContactListCreateView(generics.ListCreateAPIView):
    """
    GET: List contacts (filtered by ownership for staff users)
    POST: Create a new contact
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'organization_name']
    ordering_fields = ['last_name', 'first_name', 'created_at', 'last_gift_date', 'total_given']
    ordering = ['last_name', 'first_name']
    filterset_class = ContactFilterSet

    def get_queryset(self):
        user = self.request.user

        visible = get_visible_user_ids(user, request=self.request)
        queryset = Contact.objects.filter(owner_id__in=visible)

        # Exclude merged contacts from the list
        queryset = queryset.filter(is_merged=False)

        # Optional owner filter for admin/supervisor (intentionally NOT in FilterSet - security)
        owner_id = self.request.query_params.get('owner')
        if owner_id and user.role in ['admin', 'supervisor', 'coach']:
            queryset = queryset.filter(owner_id=owner_id)

        return queryset.select_related('owner')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ContactCreateSerializer
        return ContactListSerializer


@extend_schema_view(
    get=extend_schema(tags=['contacts'], summary='Get contact details'),
    put=extend_schema(tags=['contacts'], summary='Update contact'),
    patch=extend_schema(tags=['contacts'], summary='Partial update contact'),
    delete=extend_schema(tags=['contacts'], summary='Delete contact')
)
class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve contact details
    PATCH/PUT: Update contact
    DELETE: Delete contact
    """
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess, IsSupervisorWriteRestricted]

    def get_queryset(self):
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        queryset = Contact.objects.filter(owner_id__in=visible)
        return queryset.filter(is_merged=False).select_related(
            'owner'
        ).prefetch_related('recurring_gifts', 'groups')

    def get_serializer_class(self):
        return ContactDetailSerializer


class ContactThankView(APIView):
    """
    POST: Mark contact as thanked
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['contacts'],
        summary='Mark contact as thanked',
        description='Mark a contact as thanked and clear their needs_thank_you flag.',
        responses={200: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}}
    )
    def post(self, request, pk):
        user = request.user
        try:
            visible = get_visible_user_ids(user, request=request)
            contact = Contact.objects.get(pk=pk, owner_id__in=visible, is_merged=False)
        except Contact.DoesNotExist:
            return Response(
                {'detail': 'Contact not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        contact.mark_thanked()
        return Response({'detail': 'Contact marked as thanked.'})


@extend_schema(tags=['contacts'], summary='List contact gifts')
class ContactGiftsView(generics.ListAPIView):
    """
    GET: List gifts for a specific contact
    """
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]
    pagination_class = None

    def get_queryset(self):
        from apps.gifts.models import Gift

        contact_id = self.kwargs.get('pk')
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        return Gift.objects.filter(
            donor_contact_id=contact_id, donor_contact__owner_id__in=visible
        ).select_related(
            'donor_contact', 'donor_contact__owner', 'fund', 'recurring_gift'
        ).order_by('-gift_date')

    def get_serializer_class(self):
        from apps.gifts.serializers import GiftSerializer
        return GiftSerializer


@extend_schema(tags=['contacts'], summary='List contact recurring gifts')
class ContactRecurringGiftsView(generics.ListAPIView):
    """
    GET: List recurring gifts for a specific contact
    """
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]
    pagination_class = None

    def get_queryset(self):
        from apps.gifts.models import RecurringGift

        contact_id = self.kwargs.get('pk')
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        return RecurringGift.objects.filter(
            donor_contact_id=contact_id, donor_contact__owner_id__in=visible
        ).select_related(
            'donor_contact', 'donor_contact__owner', 'fund'
        ).order_by('-start_date')

    def get_serializer_class(self):
        from apps.gifts.serializers import RecurringGiftSerializer
        return RecurringGiftSerializer


@extend_schema(tags=['contacts'], summary='List contact tasks')
class ContactTasksView(generics.ListAPIView):
    """
    GET: List tasks for a specific contact
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        from apps.tasks.models import Task

        contact_id = self.kwargs.get('pk')
        user = self.request.user

        queryset = Task.objects.filter(contact_id=contact_id)

        visible = get_visible_user_ids(user, request=self.request)
        queryset = queryset.filter(owner_id__in=visible)

        return queryset.select_related('contact', 'owner').order_by('due_date')

    def get_serializer_class(self):
        from apps.tasks.serializers import TaskSerializer
        return TaskSerializer


class ContactEmailsView(APIView):
    """
    GET: Return email addresses for the user's contacts, respecting the
    same filters as the contact list (status, search, group, owner, etc.).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        visible = get_visible_user_ids(user, request=request)
        queryset = Contact.objects.filter(owner_id__in=visible, is_merged=False)

        # Apply owner filter (same logic as ContactListCreateView)
        owner_id = request.query_params.get('owner')
        if owner_id and user.role in ['admin', 'supervisor', 'coach']:
            queryset = queryset.filter(owner_id=owner_id)

        # Apply ContactFilterSet (status, needs_thank_you, date range, group)
        filterset = ContactFilterSet(request.query_params, queryset=queryset)
        if filterset.is_valid():
            queryset = filterset.qs

        # Apply search filter (same fields as ContactListCreateView)
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(organization_name__icontains=search)
            )

        emails = list(
            queryset.exclude(email__isnull=True).exclude(email='')
            .values_list('email', flat=True)
            .order_by('email')
        )
        return Response({'emails': emails, 'count': len(emails)})


@extend_schema(
    tags=['contacts'],
    summary='Search contacts',
    parameters=[OpenApiParameter(name='q', description='Search query', type=str, required=True)]
)
class ContactSearchView(generics.ListAPIView):
    """
    GET: Search contacts across multiple fields
    """
    serializer_class = ContactListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        query = self.request.query_params.get('q', '')

        visible = get_visible_user_ids(user, request=self.request)
        queryset = Contact.objects.filter(owner_id__in=visible)

        queryset = queryset.filter(is_merged=False)

        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query) |
                Q(organization_name__icontains=query)
            )

        return queryset[:50]  # Limit search results


@extend_schema(tags=['contacts'], summary='List contact journal memberships')
class ContactJournalsView(generics.ListAPIView):
    """
    GET: List all journals this contact belongs to with stage and decision
    """
    serializer_class = ContactJournalMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]
    pagination_class = None

    def get_queryset(self):
        from apps.journals.models import JournalStageEvent, Decision

        contact_id = self.kwargs.get('pk')
        user = self.request.user

        # Optimized query with prefetching per RESEARCH.md
        memberships = JournalContact.objects.filter(
            contact_id=contact_id
        ).select_related(
            'journal'  # ForeignKey - single JOIN
        ).prefetch_related(
            Prefetch(
                'stage_events',
                queryset=JournalStageEvent.objects.order_by('-created_at'),
                to_attr='prefetched_events'
            ),
            Prefetch(
                'decisions',
                queryset=Decision.objects.all(),
                to_attr='prefetched_decisions'
            )
        ).order_by('-created_at')

        # Filter by ownership using visibility helper
        visible = get_visible_user_ids(user, request=self.request)
        memberships = memberships.filter(journal__owner_id__in=visible)

        return memberships


@extend_schema(tags=['contacts'], summary='List contact prayer intentions')
class ContactPrayerIntentionsView(generics.ListAPIView):
    """
    GET: List prayer intentions for a specific contact (owner-scoped)
    """
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]

    def get_queryset(self):
        from apps.prayers.models import PrayerIntention

        contact_id = self.kwargs.get('pk')
        user = self.request.user
        qs = PrayerIntention.objects.filter(
            contact_id=contact_id
        ).select_related('contact')
        visible = get_visible_user_ids(user, request=self.request)
        qs = qs.filter(contact__owner_id__in=visible)
        return qs.order_by('-created_at')

    def get_serializer_class(self):
        from apps.prayers.serializers import PrayerIntentionSerializer
        return PrayerIntentionSerializer


@extend_schema(tags=['contacts'], summary='List contact journal events')
class ContactJournalEventsView(generics.ListAPIView):
    """GET: All journal stage events for a contact across all journals."""
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]
    pagination_class = StandardPagination

    def get_queryset(self):
        contact_id = self.kwargs['pk']
        user = self.request.user
        qs = JournalStageEvent.objects.filter(
            journal_contact__contact_id=contact_id,
        ).select_related(
            'journal_contact__journal',
            'journal_contact__contact',
            'triggered_by',
        ).order_by('-created_at')
        visible = get_visible_user_ids(user, request=self.request)
        qs = qs.filter(journal_contact__journal__owner_id__in=visible)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        data = [
            {
                'id': str(e.id),
                'event_type': e.event_type,
                'stage': e.stage,
                'notes': e.notes,
                'metadata': e.metadata,
                'created_at': e.created_at.isoformat(),
                'journal_name': e.journal_contact.journal.name,
                'journal_id': str(e.journal_contact.journal.id),
                'journal_contact_id': str(e.journal_contact.id),
            }
            for e in (page or qs)
        ]
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)


class DuplicateCheckView(APIView):
    """POST: Check for duplicates before creating a contact."""
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]

    @extend_schema(tags=['contacts'], summary='Check for duplicate contacts')
    def post(self, request):
        ser = DuplicateCheckSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        duplicates = find_duplicates_for_contact(
            contact_data=ser.validated_data,
            owner_id=request.user.id,
        )
        out = DuplicateMatchSerializer(duplicates, many=True)
        return Response(out.data)


class MergeContactsView(APIView):
    """POST: Merge two contacts."""
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]

    @extend_schema(tags=['contacts'], summary='Merge two contacts')
    def post(self, request):
        ser = MergeRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        # Verify both contacts are visible to the requesting user
        visible = get_visible_user_ids(request.user, request=request)
        try:
            survivor_contact = Contact.objects.get(pk=ser.validated_data['survivor_id'], owner_id__in=visible)
            loser_contact = Contact.objects.get(pk=ser.validated_data['loser_id'], owner_id__in=visible)
        except Contact.DoesNotExist:
            return Response({'detail': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)
        if survivor_contact.owner_id != loser_contact.owner_id:
            return Response({'detail': 'Contacts must belong to the same owner.'}, status=status.HTTP_400_BAD_REQUEST)
        # Only the contact owner or an admin can perform merges
        if request.user.role != 'admin' and survivor_contact.owner_id != request.user.id:
            return Response({'detail': 'You do not have permission to merge these contacts.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            survivor = merge_contacts(
                survivor_id=ser.validated_data['survivor_id'],
                loser_id=ser.validated_data['loser_id'],
                merged_by=request.user,
            )
        except (Contact.DoesNotExist, ValueError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ContactDetailSerializer(survivor).data)


class DismissDuplicateView(APIView):
    """POST: Dismiss a duplicate pair so it won't be flagged again."""
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]

    @extend_schema(tags=['contacts'], summary='Dismiss duplicate pair')
    def post(self, request):
        ser = DismissRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        # Verify both contacts exist and are visible to the user
        visible = get_visible_user_ids(request.user, request=request)
        try:
            contact_a = Contact.objects.get(pk=ser.validated_data['contact_a_id'], owner_id__in=visible)
            contact_b = Contact.objects.get(pk=ser.validated_data['contact_b_id'], owner_id__in=visible)
        except Contact.DoesNotExist:
            return Response({'detail': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Only the contact owner or an admin can dismiss duplicates
        if request.user.role != 'admin' and contact_a.owner_id != request.user.id:
            return Response({'detail': 'You do not have permission to dismiss these duplicates.'}, status=status.HTTP_403_FORBIDDEN)
        a_id = ser.validated_data['contact_a_id']
        b_id = ser.validated_data['contact_b_id']
        if str(a_id) > str(b_id):
            a_id, b_id = b_id, a_id
        DismissedDuplicate.objects.get_or_create(
            contact_a_id=a_id,
            contact_b_id=b_id,
            defaults={'dismissed_by': request.user},
        )
        return Response({'detail': 'Pair dismissed.'}, status=status.HTTP_201_CREATED)
