"""
Views for Prayer Intention API endpoints.
"""
import hashlib

from django.db.models import Case, Value, When
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import get_visible_user_ids
from apps.prayers.filters import PrayerIntentionFilterSet
from apps.prayers.models import PrayerIntention
from apps.prayers.serializers import PrayerIntentionSerializer


def _owner_scoped_queryset(user):
    """Return PrayerIntention queryset scoped by ownership."""
    qs = PrayerIntention.objects.select_related('contact').all()
    visible = get_visible_user_ids(user)
    if visible is not None:
        qs = qs.filter(contact__owner_id__in=visible)
    return qs


class PrayerIntentionListCreateView(generics.ListCreateAPIView):
    """
    GET: List prayer intentions (owner-scoped)
    POST: Create a new prayer intention
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrayerIntentionSerializer
    filterset_class = PrayerIntentionFilterSet
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'contact__first_name', 'contact__last_name']
    ordering_fields = ['created_at', 'status', 'last_prayed_at']

    def get_queryset(self):
        return _owner_scoped_queryset(self.request.user).annotate(
            status_order=Case(
                When(status='active', then=Value(0)),
                When(status='answered', then=Value(1)),
                When(status='archived', then=Value(2)),
                default=Value(3),
            )
        ).order_by('status_order', '-created_at')


class PrayerIntentionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve prayer intention details
    PATCH/PUT: Update prayer intention (with status timestamp management)
    DELETE: Delete prayer intention
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrayerIntentionSerializer

    def get_queryset(self):
        return _owner_scoped_queryset(self.request.user)


class MarkPrayedView(APIView):
    """
    POST: Mark a prayer intention as prayed (sets last_prayed_at to now).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        qs = _owner_scoped_queryset(request.user)
        try:
            intention = qs.get(pk=pk)
        except PrayerIntention.DoesNotExist:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        intention.last_prayed_at = timezone.now()
        intention.save(update_fields=['last_prayed_at'])
        return Response({'detail': 'Marked as prayed.'})


class TodaysFocusView(generics.ListAPIView):
    """
    GET: Return today's curated set of active prayer intentions.

    Prioritizes never-prayed (nulls first), then oldest last_prayed_at.
    Uses deterministic daily rotation based on hash of date + user pk.
    Limited to min(5, total active intentions).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrayerIntentionSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        qs = _owner_scoped_queryset(user).filter(status='active')

        # Deterministic daily rotation: compute offset from hash of date + user pk
        today_str = timezone.now().date().isoformat()
        hash_input = f"{today_str}:{user.pk}"
        hash_val = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)

        # Order: never-prayed first (nulls first), then oldest last_prayed_at
        ordered = qs.order_by(
            Case(
                When(last_prayed_at__isnull=True, then=Value(0)),
                default=Value(1),
            ),
            'last_prayed_at',
            'created_at',
        )

        total = ordered.count()
        if total == 0:
            return ordered.none()

        limit = min(5, total)
        offset = hash_val % total

        # Wrap around: pick `limit` items starting at offset
        pks = list(ordered.values_list('pk', flat=True))
        selected_pks = []
        for i in range(limit):
            selected_pks.append(pks[(offset + i) % total])

        # Preserve the ordering from the selected set
        preserved = Case(
            *[When(pk=pk, then=Value(i)) for i, pk in enumerate(selected_pks)]
        )
        return PrayerIntention.objects.select_related('contact').filter(
            pk__in=selected_pks
        ).annotate(focus_order=preserved).order_by('focus_order')
