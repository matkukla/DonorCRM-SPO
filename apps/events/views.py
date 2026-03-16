"""
Views for Event management.
"""
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import get_visible_user_ids
from apps.events.models import Event
from apps.events.serializers import EventSerializer


class EventListView(generics.ListAPIView):
    """
    GET: List events/notifications for current user
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    filterset_fields = ['event_type', 'severity', 'is_read', 'is_new']

    def get_queryset(self):
        user = self.request.user

        # finance/read_only roles (visible is None) can see all events when ?all is passed
        visible = get_visible_user_ids(user, request=self.request)
        if visible is None and self.request.query_params.get('all'):
            return Event.objects.all()
        if visible is not None:
            return Event.objects.filter(user_id__in=visible).select_related('contact')
        return Event.objects.filter(user=user).select_related('contact')


class EventDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve event details
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        visible = get_visible_user_ids(user, request=self.request)
        if visible is None:
            return Event.objects.all()
        return Event.objects.filter(user_id__in=visible)


class EventMarkReadView(APIView):
    """
    POST: Mark event as read
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            event = Event.objects.get(pk=pk, user=request.user)
        except Event.DoesNotExist:
            return Response(
                {'detail': 'Event not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        event.mark_read()
        return Response({'detail': 'Event marked as read.'})


class EventMarkAllReadView(APIView):
    """
    POST: Mark all events as read
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = Event.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response({'detail': f'Marked {count} events as read.'})


class UnreadEventCountView(APIView):
    """
    GET: Get count of unread events
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        effective_user = getattr(request, 'view_as_user', None) or request.user
        counts = Event.objects.filter(user=effective_user).aggregate(
            unread_count=Count('id', filter=models.Q(is_read=False)),
            new_count=Count('id', filter=models.Q(is_new=True))
        )

        return Response({
            'unread_count': counts['unread_count'] or 0,
            'new_count': counts['new_count'] or 0
        })


# Import for the aggregate query
from django.db import models
