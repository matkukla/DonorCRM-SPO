"""
Views for Gift and RecurringGift CRUD API endpoints.
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions

from apps.gifts.filters import GiftFilterSet, RecurringGiftFilterSet
from apps.gifts.models import Gift, RecurringGift
from apps.gifts.serializers import (
    GiftCreateSerializer,
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
    filter_backends = [DjangoFilterBackend]
    filterset_class = GiftFilterSet
    ordering = ['-gift_date']

    def get_queryset(self):
        user = self.request.user
        qs = Gift.objects.select_related('donor_contact', 'fund').all()
        if user.role not in ['admin', 'finance', 'read_only']:
            qs = qs.filter(donor_contact__owner=user)
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
    GET: Retrieve gift details
    PUT/PATCH: Update gift
    DELETE: Delete gift
    """
    serializer_class = GiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Gift.objects.select_related('donor_contact', 'fund').all()
        if user.role not in ['admin', 'finance', 'read_only']:
            qs = qs.filter(donor_contact__owner=user)
        return qs


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
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecurringGiftFilterSet
    ordering = ['-start_date']

    def get_queryset(self):
        user = self.request.user
        qs = RecurringGift.objects.select_related('donor_contact', 'fund').all()
        if user.role not in ['admin', 'finance', 'read_only']:
            qs = qs.filter(donor_contact__owner=user)
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = RecurringGift.objects.select_related('donor_contact', 'fund').all()
        if user.role not in ['admin', 'finance', 'read_only']:
            qs = qs.filter(donor_contact__owner=user)
        return qs
