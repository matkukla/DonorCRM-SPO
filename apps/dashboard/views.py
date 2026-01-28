"""
Views for Dashboard data.
"""
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.services import (
    get_dashboard_summary,
    get_giving_summary,
    get_late_donations,
    get_monthly_gifts,
    get_needs_attention,
    get_recent_gifts,
    get_recent_journal_activity,
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


class LateDonationsView(APIView):
    """
    GET: Get late donations (active pledges past due)
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['dashboard'],
        summary='Get late donations',
        parameters=[OpenApiParameter(name='limit', description='Max results (default: 10)', type=int)]
    )
    def get(self, request):
        user = request.user
        limit = int(request.query_params.get('limit', 10))

        late_donations = get_late_donations(user, limit=limit)

        return Response({
            'late_donations': late_donations,
            'total_count': len(late_donations),
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


class RecentJournalActivityView(APIView):
    """
    GET: Get recent journal stage events
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['dashboard'], summary='Get recent journal activity')
    def get(self, request):
        return Response({
            'journal_activity': get_recent_journal_activity(request.user),
        })


class GivingSummaryView(APIView):
    """
    GET: Get giving summary (Given & Expecting widget data)
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['dashboard'],
        summary='Get giving summary',
        parameters=[OpenApiParameter(name='year', description='Calendar year (default: current)', type=int)]
    )
    def get(self, request):
        year = request.query_params.get('year')
        year = int(year) if year else None
        return Response(get_giving_summary(request.user, year=year))


class MonthlyGiftsView(APIView):
    """
    GET: Get monthly gift totals for bar chart
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['dashboard'],
        summary='Get monthly gifts',
        parameters=[OpenApiParameter(name='months', description='Number of months (default: 12)', type=int)]
    )
    def get(self, request):
        months = int(request.query_params.get('months', 12))
        return Response(get_monthly_gifts(request.user, months=months))
