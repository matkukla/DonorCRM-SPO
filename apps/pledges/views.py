"""
Views for Pledge management.
"""
from django.db.models import Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsContactOwnerOrReadAccess
from apps.pledges.models import Pledge, PledgeStatus
from apps.pledges.serializers import (
    PledgeCreateSerializer,
    PledgeSerializer,
)


class PledgeListCreateView(generics.ListCreateAPIView):
    """
    GET: List pledges
    POST: Create a new pledge
    """
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at', 'amount', 'start_date']
    ordering = ['-created_at']
    filterset_fields = ['status', 'frequency', 'is_late']
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin and Finance can see all pledges
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Pledge.objects.all()
        else:
            # Staffs see only pledges for their contacts
            queryset = Pledge.objects.filter(contact__owner=user)

        # Contact filter
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)

        return queryset.select_related('contact')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PledgeCreateSerializer
        return PledgeSerializer


class PledgeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve pledge details
    PATCH/PUT: Update pledge
    DELETE: Delete pledge (admin only)
    """
    serializer_class = PledgeSerializer
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            return Pledge.objects.all()
        return Pledge.objects.filter(contact__owner=user)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can delete pledges.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class PledgePauseView(APIView):
    """
    POST: Pause an active pledge
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        try:
            if user.role == 'admin':
                pledge = Pledge.objects.get(pk=pk)
            else:
                pledge = Pledge.objects.get(pk=pk, contact__owner=user)
        except Pledge.DoesNotExist:
            return Response(
                {'detail': 'Pledge not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if pledge.status != PledgeStatus.ACTIVE:
            return Response(
                {'detail': 'Only active pledges can be paused.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pledge.pause()
        return Response({'detail': 'Pledge paused.'})


class PledgeResumeView(APIView):
    """
    POST: Resume a paused pledge
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        try:
            if user.role == 'admin':
                pledge = Pledge.objects.get(pk=pk)
            else:
                pledge = Pledge.objects.get(pk=pk, contact__owner=user)
        except Pledge.DoesNotExist:
            return Response(
                {'detail': 'Pledge not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if pledge.status != PledgeStatus.PAUSED:
            return Response(
                {'detail': 'Only paused pledges can be resumed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pledge.resume()
        return Response({'detail': 'Pledge resumed.'})


class PledgeCancelView(APIView):
    """
    POST: Cancel a pledge
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        try:
            if user.role == 'admin':
                pledge = Pledge.objects.get(pk=pk)
            else:
                pledge = Pledge.objects.get(pk=pk, contact__owner=user)
        except Pledge.DoesNotExist:
            return Response(
                {'detail': 'Pledge not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if pledge.status in [PledgeStatus.CANCELLED, PledgeStatus.COMPLETED]:
            return Response(
                {'detail': 'Pledge is already cancelled or completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pledge.cancel()
        return Response({'detail': 'Pledge cancelled.'})


class LatePledgesView(generics.ListAPIView):
    """
    GET: List late pledges
    """
    serializer_class = PledgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role in ['admin', 'finance', 'read_only']:
            return Pledge.objects.filter(is_late=True)
        return Pledge.objects.filter(contact__owner=user, is_late=True)


class PledgeSummaryView(APIView):
    """
    GET: Get pledge summary statistics
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Base queryset
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Pledge.objects.all()
        else:
            queryset = Pledge.objects.filter(contact__owner=user)

        active_pledges = queryset.filter(status=PledgeStatus.ACTIVE)

        # Calculate totals
        stats = active_pledges.aggregate(
            count=Count('id'),
            late_count=Count('id', filter=models.Q(is_late=True))
        )

        # Calculate monthly equivalent (need to iterate for frequency conversion)
        total_monthly = sum(p.monthly_equivalent for p in active_pledges)

        return Response({
            'total_monthly_pledges': total_monthly,
            'active_pledge_count': stats['count'] or 0,
            'late_pledge_count': stats['late_count'] or 0,
            'total_pledged_annually': total_monthly * 12
        })


# Import models for the aggregate query
from django.db import models
