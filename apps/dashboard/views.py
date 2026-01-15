"""
Views for Dashboard data.
"""
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.services import (
    get_at_risk_donors,
    get_dashboard_summary,
    get_needs_attention,
    get_recent_gifts,
    get_support_progress,
    get_thank_you_queue,
    get_what_changed,
)
from apps.events.services import mark_events_as_not_new


class DashboardView(APIView):
    """
    GET: Get complete dashboard data
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['dashboard'], summary='Get complete dashboard data')
    def get(self, request):
        user = request.user
        data = get_dashboard_summary(user)

        # Mark events as not new (user has seen dashboard)
        mark_events_as_not_new(user)

        return Response(data)


class WhatChangedView(APIView):
    """
    GET: Get events/changes since last login
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['dashboard'], summary='Get changes since last login')
    def get(self, request):
        user = request.user
        data = get_what_changed(user)

        # Serialize events
        from apps.events.serializers import EventSerializer
        data['recent_events'] = EventSerializer(data['recent_events'], many=True).data

        return Response(data)


class NeedsAttentionView(APIView):
    """
    GET: Get items requiring action
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['dashboard'], summary='Get items needing attention')
    def get(self, request):
        user = request.user
        data = get_needs_attention(user)

        # Serialize related objects
        from apps.pledges.serializers import PledgeSerializer
        from apps.tasks.serializers import TaskSerializer
        from apps.contacts.serializers import ContactListSerializer

        data['late_pledges'] = PledgeSerializer(data['late_pledges'], many=True).data
        data['overdue_tasks'] = TaskSerializer(data['overdue_tasks'], many=True).data
        data['tasks_due_today'] = TaskSerializer(data['tasks_due_today'], many=True).data
        data['thank_you_needed'] = ContactListSerializer(data['thank_you_needed'], many=True).data

        return Response(data)


class AtRiskView(APIView):
    """
    GET: Get at-risk donors
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['dashboard'],
        summary='Get at-risk donors',
        parameters=[OpenApiParameter(name='days', description='Days threshold for at-risk (default: 60)', type=int)]
    )
    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 60))

        donors = get_at_risk_donors(user, days_threshold=days)

        from apps.contacts.serializers import ContactListSerializer
        serializer = ContactListSerializer(donors[:20], many=True)

        return Response({
            'at_risk_donors': serializer.data,
            'total_count': donors.count(),
            'threshold_days': days
        })


class ThankYouQueueView(APIView):
    """
    GET: Get thank-you queue
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['dashboard'], summary='Get thank-you queue')
    def get(self, request):
        user = request.user
        contacts = get_thank_you_queue(user)

        from apps.contacts.serializers import ContactListSerializer
        serializer = ContactListSerializer(contacts[:20], many=True)

        return Response({
            'thank_you_queue': serializer.data,
            'total_count': contacts.count()
        })


class SupportProgressView(APIView):
    """
    GET: Get support progress toward goal
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['dashboard'], summary='Get support progress toward goal')
    def get(self, request):
        user = request.user
        data = get_support_progress(user)
        return Response(data)


class RecentGiftsView(APIView):
    """
    GET: Get recent donations
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['dashboard'],
        summary='Get recent gifts',
        parameters=[
            OpenApiParameter(name='days', description='Number of days (default: 30)', type=int),
            OpenApiParameter(name='limit', description='Max results (default: 10)', type=int),
        ]
    )
    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))

        gifts = get_recent_gifts(user, days=days, limit=limit)

        from apps.donations.serializers import DonationSerializer
        serializer = DonationSerializer(gifts, many=True)

        return Response({
            'recent_gifts': serializer.data,
            'days': days
        })
