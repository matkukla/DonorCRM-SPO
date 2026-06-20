"""
Views for Dashboard data.
"""

import uuid

from rest_framework import permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.permissions import get_visible_user_ids, is_financial_role
from apps.core.utils import get_safe_int_param
from apps.dashboard.services import (
    get_dashboard_summary,
    get_giving_summary,
    get_late_donations,
    get_monthly_gifts,
    get_needs_attention,
    get_recent_gifts,
    get_support_progress,
    get_thank_you_queue,
    get_what_changed,
)
from apps.events.services import mark_events_as_not_new
from apps.users.models import User


def _authorize_dashboard_target(user, target_uuid, request):
    """Authorize ``user`` to view ``target_uuid``'s dashboard, or raise.

    Runs BEFORE any existence lookup so an unauthorized id and a non-existent id are
    indistinguishable to non-admins — no user enumeration (ADR 0001):
      - Admin: may select any active user.
      - Supervisor: only missionaries ASSIGNED to them — the same boundary the
        View-As middleware enforces (``supervised_users``).
      - Other roles: only users within their get_visible_user_ids() set.
    """
    if user.role == "admin":
        return
    if user.role == "supervisor":
        # Assigned, active missionaries only. .exists() on the assignment set IS the
        # authorization: a non-existent or unassigned id simply isn't in it -> 403.
        if user.supervised_users.filter(pk=target_uuid, is_active=True).exists():
            return
        raise PermissionDenied("You do not have permission to view this user's dashboard.")
    if target_uuid not in get_visible_user_ids(user, request=request):
        raise PermissionDenied("You do not have permission to view this user's dashboard.")


def _resolve_target_user(request):
    """Resolve the target user for dashboard data.

    If ?user_id= is provided, return that user if the requester is authorized by
    _authorize_dashboard_target() (admin: any; supervisor: assigned missionaries;
    others: their get_visible_user_ids() set). The authorization check runs before
    the existence lookup, so unauthorized ids return 403, not 404.

    Without ?user_id= (or when ?user_id= matches self), returns the requesting user.
    Default data scoping (what shows in list views) is governed separately by
    get_visible_user_ids() and is not affected by this function.
    """
    user = request.user
    target_user_id = request.query_params.get("user_id")

    if target_user_id and str(target_user_id) != str(user.id):
        try:
            target_uuid = uuid.UUID(target_user_id)
        except ValueError:
            raise NotFound("User not found.")
        _authorize_dashboard_target(user, target_uuid, request)
        target_user = User.objects.filter(id=target_uuid, is_active=True).first()
        if not target_user:
            raise NotFound("User not found.")
        return target_user
    return user


class DashboardView(APIView):
    """
    GET: Get complete dashboard data
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Get complete dashboard data")
    def get(self, request):
        target = _resolve_target_user(request)
        # Financial detail is gated on the REQUESTER's role, not the target's — a
        # coach viewing a coached missionary still gets no individual gift detail.
        data = get_dashboard_summary(
            target, include_financial_detail=is_financial_role(request.user)
        )
        return Response(data)


class MarkEventsSeenView(APIView):
    """
    POST: Mark all new events as seen for the authenticated user.
    Separated from DashboardView.get() to avoid GET side effects (QAL-09).
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Mark events as seen")
    def post(self, request):
        mark_events_as_not_new(request.user)
        return Response({"detail": "Events marked as seen."})


class WhatChangedView(APIView):
    """
    GET: Get events/changes since last login
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Get changes since last login")
    def get(self, request):
        target = _resolve_target_user(request)
        data = get_what_changed(target, include_financial_detail=is_financial_role(request.user))

        # Serialize events
        from apps.events.serializers import EventSerializer

        data["recent_events"] = EventSerializer(data["recent_events"], many=True).data

        return Response(data)


class NeedsAttentionView(APIView):
    """
    GET: Get items requiring action
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Get items needing attention")
    def get(self, request):
        target = _resolve_target_user(request)
        data = get_needs_attention(target)

        # Serialize related objects
        from apps.contacts.serializers import ContactListSerializer
        from apps.tasks.serializers import TaskSerializer

        # late_pledges is already an empty list (no serialization needed)
        data["overdue_tasks"] = TaskSerializer(data["overdue_tasks"], many=True).data
        data["tasks_due_today"] = TaskSerializer(data["tasks_due_today"], many=True).data
        data["broadcast_tasks"] = TaskSerializer(data["broadcast_tasks"], many=True).data
        data["thank_you_needed"] = ContactListSerializer(data["thank_you_needed"], many=True).data

        return Response(data)


class LateDonationsView(APIView):
    """
    GET: Get late donations (active pledges past due)
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["dashboard"],
        summary="Get late donations",
        parameters=[
            OpenApiParameter(name="limit", description="Max results (default: 10)", type=int)
        ],
    )
    def get(self, request):
        target = _resolve_target_user(request)
        limit = get_safe_int_param(request, "limit", default=10, min_val=1, max_val=100)

        late_donations = get_late_donations(target, limit=limit)

        return Response(
            {
                "late_donations": late_donations,
                "total_count": len(late_donations),
            }
        )


class ThankYouQueueView(APIView):
    """
    GET: Get thank-you queue
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Get thank-you queue")
    def get(self, request):
        target = _resolve_target_user(request)
        contacts = get_thank_you_queue(target)

        from apps.contacts.serializers import ContactListSerializer

        serializer = ContactListSerializer(contacts[:20], many=True)

        return Response({"thank_you_queue": serializer.data, "total_count": contacts.count()})


class SupportProgressView(APIView):
    """
    GET: Get support progress toward goal
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Get support progress toward goal")
    def get(self, request):
        target = _resolve_target_user(request)
        data = get_support_progress(target)
        return Response(data)


class RecentGiftsView(APIView):
    """
    GET: Get recent donations
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["dashboard"],
        summary="Get recent gifts",
        parameters=[
            OpenApiParameter(name="days", description="Number of days (default: 30)", type=int),
            OpenApiParameter(name="limit", description="Max results (default: 10)", type=int),
        ],
    )
    def get(self, request):
        target = _resolve_target_user(request)
        days = get_safe_int_param(request, "days", default=30, min_val=1, max_val=365)
        limit = get_safe_int_param(request, "limit", default=10, min_val=1, max_val=100)

        # Individual gift rows are financial detail — withheld from non-financial
        # requesters (coach), PRD fix #2.
        if not is_financial_role(request.user):
            return Response({"recent_gifts": [], "days": days})

        gifts = get_recent_gifts(target, days=days, limit=limit)

        from apps.gifts.serializers import GiftSerializer

        serializer = GiftSerializer(gifts, many=True)

        return Response({"recent_gifts": serializer.data, "days": days})


class GivingSummaryView(APIView):
    """
    GET: Get giving summary (Given & Expecting widget data)
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["dashboard"],
        summary="Get giving summary (fiscal year Jun 1 - May 31)",
    )
    def get(self, request):
        target = _resolve_target_user(request)
        return Response(get_giving_summary(target))


class MonthlyGiftsView(APIView):
    """
    GET: Get monthly gift totals for bar chart
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["dashboard"],
        summary="Get monthly gifts",
        parameters=[
            OpenApiParameter(name="months", description="Number of months (default: 12)", type=int)
        ],
    )
    def get(self, request):
        target = _resolve_target_user(request)
        months = get_safe_int_param(request, "months", default=12, min_val=1, max_val=60)
        return Response(get_monthly_gifts(target, months=months))


class UserDashboardLayoutView(APIView):
    """GET: Get a specific user's dashboard layout (for supervisor/admin viewing)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Get user dashboard layout")
    def get(self, request, pk):
        try:
            pk = uuid.UUID(pk) if not isinstance(pk, uuid.UUID) else pk
        except ValueError:
            raise NotFound("User not found.")
        if str(pk) != str(request.user.id):
            _authorize_dashboard_target(request.user, pk, request)
        target = User.objects.filter(id=pk, is_active=True).first()
        if not target:
            raise NotFound("User not found.")
        return Response({"dashboard_layout": target.dashboard_layout or {}})
