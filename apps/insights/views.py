"""
Views for Insights/Reports data.
"""
from datetime import datetime

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.insights.services import (
    get_donations_by_month,
    get_donations_by_year,
    get_follow_ups,
    get_late_donations,
    get_monthly_commitments,
    get_review_queue,
    get_transactions,
)


class DonationsByMonthView(APIView):
    """
    GET: Get donation totals grouped by month for a year.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['insights'],
        summary='Get donations by month',
        parameters=[
            OpenApiParameter(name='year', description='Calendar year (default: current)', type=int)
        ]
    )
    def get(self, request):
        year = request.query_params.get('year')
        year = int(year) if year else None
        return Response(get_donations_by_month(request.user, year=year))


class DonationsByYearView(APIView):
    """
    GET: Get donation totals grouped by year.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['insights'],
        summary='Get donations by year',
        parameters=[
            OpenApiParameter(name='years', description='Number of years to include (default: 5)', type=int)
        ]
    )
    def get(self, request):
        years = int(request.query_params.get('years', 5))
        return Response(get_donations_by_year(request.user, years=years))


class MonthlyCommitmentsView(APIView):
    """
    GET: Get summary of active recurring pledges.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['insights'], summary='Get monthly commitments')
    def get(self, request):
        return Response(get_monthly_commitments(request.user))


class LateDonationsView(APIView):
    """
    GET: Get pledges with late donations.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['insights'],
        summary='Get late donations',
        parameters=[
            OpenApiParameter(name='limit', description='Max results (default: 50)', type=int)
        ]
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 50))
        return Response(get_late_donations(request.user, limit=limit))


class FollowUpsView(APIView):
    """
    GET: Get incomplete tasks needing follow-up.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['insights'],
        summary='Get follow-ups',
        parameters=[
            OpenApiParameter(name='limit', description='Max results (default: 50)', type=int)
        ]
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 50))
        return Response(get_follow_ups(request.user, limit=limit))


class ReviewQueueView(APIView):
    """
    GET: Get items pending admin review.
    Admin-only endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['insights'], summary='Get review queue (admin only)')
    def get(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Admin access required'}, status=403)
        return Response(get_review_queue(request.user))


class TransactionsView(APIView):
    """
    GET: Get full transaction ledger.
    Admin/finance-only endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['insights'],
        summary='Get transactions ledger (admin/finance only)',
        parameters=[
            OpenApiParameter(name='limit', description='Max results (default: 100)', type=int),
            OpenApiParameter(name='offset', description='Offset for pagination (default: 0)', type=int),
            OpenApiParameter(name='contact_id', description='Filter by contact ID', type=str),
            OpenApiParameter(name='date_from', description='Filter by start date (YYYY-MM-DD)', type=str),
            OpenApiParameter(name='date_to', description='Filter by end date (YYYY-MM-DD)', type=str),
        ]
    )
    def get(self, request):
        if request.user.role not in ['admin', 'finance']:
            return Response({'detail': 'Admin or finance access required'}, status=403)

        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))
        contact_id = request.query_params.get('contact_id')

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        return Response(get_transactions(
            request.user,
            limit=limit,
            offset=offset,
            contact_id=contact_id,
            date_from=date_from,
            date_to=date_to,
        ))
