"""
Views for Gift and RecurringGift CRUD API endpoints.
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.gifts.filters import GiftFilterSet, RecurringGiftFilterSet
from apps.gifts.models import Gift, RecurringGift
from apps.core.permissions import IsSupervisorWriteRestricted, get_visible_user_ids
from apps.gifts.serializers import (
    GiftCreateSerializer,
    GiftDetailSerializer,
    GiftSerializer,
    RecurringGiftCreateSerializer,
    RecurringGiftSerializer,
)


@extend_schema_view(
    get=extend_schema(tags=['gifts'], summary='List gifts'),
    post=extend_schema(tags=['gifts'], summary='Create gift'),
)
class GiftListCreateView(generics.ListCreateAPIView):
    """
    GET: List gifts (filtered by ownership for staff users)
    POST: Create a new gift
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GiftFilterSet
    search_fields = ['donor_contact__first_name', 'donor_contact__last_name', 'description']
    ordering_fields = ['gift_date', 'amount_cents', 'created_at']
    ordering = ['-gift_date']

    def get_queryset(self):
        user = self.request.user
        qs = Gift.objects.select_related('donor_contact', 'fund').all()
        visible = get_visible_user_ids(user)
        if visible is not None:
            qs = qs.filter(donor_contact__owner_id__in=visible)
        return qs.order_by('-gift_date')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return GiftCreateSerializer
        return GiftSerializer


@extend_schema_view(
    get=extend_schema(tags=['gifts'], summary='Get gift details'),
    put=extend_schema(tags=['gifts'], summary='Update gift'),
    patch=extend_schema(tags=['gifts'], summary='Partial update gift'),
    delete=extend_schema(tags=['gifts'], summary='Delete gift'),
)
class GiftDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve gift details with solicitor credits
    PUT/PATCH: Update gift
    DELETE: Delete gift
    """
    permission_classes = [permissions.IsAuthenticated, IsSupervisorWriteRestricted]

    def get_queryset(self):
        user = self.request.user
        qs = Gift.objects.select_related('donor_contact', 'fund').prefetch_related(
            'credits__solicitor'
        ).all()
        visible = get_visible_user_ids(user)
        if visible is not None:
            qs = qs.filter(donor_contact__owner_id__in=visible)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return GiftDetailSerializer
        return GiftSerializer


@extend_schema_view(
    get=extend_schema(tags=['gifts'], summary='List recurring gifts'),
    post=extend_schema(tags=['gifts'], summary='Create recurring gift'),
)
class RecurringGiftListCreateView(generics.ListCreateAPIView):
    """
    GET: List recurring gifts (filtered by ownership for staff users)
    POST: Create a new recurring gift
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = RecurringGiftFilterSet
    search_fields = ['donor_contact__first_name', 'donor_contact__last_name', 'description']
    ordering_fields = ['start_date', 'amount_cents', 'status', 'frequency']
    ordering = ['-start_date']

    def get_queryset(self):
        user = self.request.user
        qs = RecurringGift.objects.select_related('donor_contact', 'fund').all()
        visible = get_visible_user_ids(user)
        if visible is not None:
            qs = qs.filter(donor_contact__owner_id__in=visible)
        return qs.order_by('-start_date')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RecurringGiftCreateSerializer
        return RecurringGiftSerializer


@extend_schema_view(
    get=extend_schema(tags=['gifts'], summary='Get recurring gift details'),
    put=extend_schema(tags=['gifts'], summary='Update recurring gift'),
    patch=extend_schema(tags=['gifts'], summary='Partial update recurring gift'),
    delete=extend_schema(tags=['gifts'], summary='Delete recurring gift'),
)
class RecurringGiftDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve recurring gift details
    PUT/PATCH: Update recurring gift
    DELETE: Delete recurring gift
    """
    serializer_class = RecurringGiftSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupervisorWriteRestricted]

    def get_queryset(self):
        user = self.request.user
        qs = RecurringGift.objects.select_related('donor_contact', 'fund').all()
        visible = get_visible_user_ids(user)
        if visible is not None:
            qs = qs.filter(donor_contact__owner_id__in=visible)
        return qs
