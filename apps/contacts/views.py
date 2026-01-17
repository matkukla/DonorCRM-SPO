"""
Views for Contact management.
"""
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contacts.models import Contact, ContactStatus
from apps.contacts.serializers import (
    ContactCreateSerializer,
    ContactDetailSerializer,
    ContactListSerializer,
)
from apps.core.permissions import IsContactOwnerOrReadAccess, IsStaffOrAbove


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
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'created_at', 'last_gift_date', 'total_given']
    ordering = ['last_name', 'first_name']
    filterset_fields = ['status', 'needs_thank_you']

    def get_queryset(self):
        user = self.request.user

        # Admin and Finance can see all contacts
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Contact.objects.all()
        else:
            # Staffs see only their own contacts
            queryset = Contact.objects.filter(owner=user)

        # Optional owner filter for admin
        owner_id = self.request.query_params.get('owner')
        if owner_id and user.role == 'admin':
            queryset = queryset.filter(owner_id=owner_id)

        # Optional group filter
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)

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
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            return Contact.objects.all()
        return Contact.objects.filter(owner=user)

    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return ContactDetailSerializer
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
            if user.role == 'admin':
                contact = Contact.objects.get(pk=pk)
            else:
                contact = Contact.objects.get(pk=pk, owner=user)
        except Contact.DoesNotExist:
            return Response(
                {'detail': 'Contact not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        contact.mark_thanked()
        return Response({'detail': 'Contact marked as thanked.'})


@extend_schema(tags=['contacts'], summary='List contact donations')
class ContactDonationsView(generics.ListAPIView):
    """
    GET: List donations for a specific contact
    """
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]

    def get_queryset(self):
        from apps.donations.models import Donation

        contact_id = self.kwargs.get('pk')
        return Donation.objects.filter(contact_id=contact_id).order_by('-date')

    def get_serializer_class(self):
        from apps.donations.serializers import DonationSerializer
        return DonationSerializer


@extend_schema(tags=['contacts'], summary='List contact pledges')
class ContactPledgesView(generics.ListAPIView):
    """
    GET: List pledges for a specific contact
    """
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]

    def get_queryset(self):
        from apps.pledges.models import Pledge

        contact_id = self.kwargs.get('pk')
        return Pledge.objects.filter(contact_id=contact_id).order_by('-created_at')

    def get_serializer_class(self):
        from apps.pledges.serializers import PledgeSerializer
        return PledgeSerializer


@extend_schema(tags=['contacts'], summary='List contact tasks')
class ContactTasksView(generics.ListAPIView):
    """
    GET: List tasks for a specific contact
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from apps.tasks.models import Task

        contact_id = self.kwargs.get('pk')
        user = self.request.user

        queryset = Task.objects.filter(contact_id=contact_id)

        # Filter by owner unless admin
        if user.role != 'admin':
            queryset = queryset.filter(owner=user)

        return queryset.order_by('due_date')

    def get_serializer_class(self):
        from apps.tasks.serializers import TaskSerializer
        return TaskSerializer


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

    def get_queryset(self):
        user = self.request.user
        query = self.request.query_params.get('q', '')

        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner=user)

        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )

        return queryset[:50]  # Limit search results
