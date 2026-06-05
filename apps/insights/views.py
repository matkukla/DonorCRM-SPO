"""
Views for Insights/Reports data.
"""


from django.db import transaction

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.models import OrgSettings
from apps.core.permissions import IsAdmin, is_financial_role
from apps.core.utils import get_safe_int_param, get_safe_year_param, validate_date_params
from apps.insights.admin_analytics_services import (
    get_fiscal_year_donations,
    get_fiscal_year_pace,
    get_missionaries_behind_goal,
    get_pipeline_funnel_with_conversion,
    get_weekly_engagement,
)
from apps.insights.serializers import (
    ConversionFunnelResponseSerializer,
    DashboardOverviewSerializer,
    FiscalYearDonationsResponseSerializer,
    FiscalYearPaceResponseSerializer,
    MissionariesBehindGoalResponseSerializer,
    OrgSettingsSerializer,
    PipelineFunnelConversionResponseSerializer,
    StageContactsResponseSerializer,
    StalledContactsResponseSerializer,
    TeamActivityResponseSerializer,
    TeamTrendsResponseSerializer,
    UserDrilldownResponseSerializer,
    UserJournalsResponseSerializer,
    UserPerformanceResponseSerializer,
    UserTrendsResponseSerializer,
    WeeklyEngagementResponseSerializer,
)
from apps.insights.services import (
    get_conversion_funnel,
    get_dashboard_overview,
    get_donations_by_month,
    get_donations_by_year,
    get_follow_ups,
    get_late_donations,
    get_monthly_commitments,
    get_single_user_performance,
    get_stage_contacts,
    get_stalled_contacts,
    get_team_activity,
    get_team_trends,
    get_transactions,
    get_user_drilldown,
    get_user_journals,
    get_user_performance,
    get_user_trends,
)


class DonationsByMonthView(APIView):
    """
    GET: Get donation totals grouped by month for a year.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["insights"],
        summary="Get donations by month",
        parameters=[
            OpenApiParameter(name="year", description="Calendar year (default: current)", type=int)
        ],
    )
    def get(self, request):
        if not is_financial_role(request.user):
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        year = get_safe_year_param(request, "year")
        return Response(get_donations_by_month(request.user, year=year, request=request))


class DonationsByYearView(APIView):
    """
    GET: Get donation totals grouped by year.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["insights"],
        summary="Get donations by year",
        parameters=[
            OpenApiParameter(
                name="years", description="Number of years to include (default: 5)", type=int
            )
        ],
    )
    def get(self, request):
        if not is_financial_role(request.user):
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        years = get_safe_int_param(request, "years", default=5, min_val=1, max_val=50)
        return Response(get_donations_by_year(request.user, years=years, request=request))


class MonthlyCommitmentsView(APIView):
    """
    GET: Get summary of active recurring pledges.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=["insights"], summary="Get monthly commitments")
    def get(self, request):
        if not is_financial_role(request.user):
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        return Response(get_monthly_commitments(request.user, request=request))


class LateDonationsView(APIView):
    """
    GET: Get pledges with late donations.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["insights"],
        summary="Get late donations",
        parameters=[
            OpenApiParameter(name="limit", description="Max results (default: 50)", type=int)
        ],
    )
    def get(self, request):
        if not is_financial_role(request.user):
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        limit = get_safe_int_param(request, "limit", default=50, min_val=1, max_val=500)
        return Response(get_late_donations(request.user, limit=limit, request=request))


class FollowUpsView(APIView):
    """
    GET: Get incomplete tasks needing follow-up.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["insights"],
        summary="Get follow-ups",
        parameters=[
            OpenApiParameter(name="limit", description="Max results (default: 50)", type=int)
        ],
    )
    def get(self, request):
        limit = get_safe_int_param(request, "limit", default=50, min_val=1, max_val=500)
        return Response(get_follow_ups(request.user, limit=limit, request=request))


class TransactionsView(APIView):
    """
    GET: Get full transaction ledger.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get transactions ledger (admin only)",
        parameters=[
            OpenApiParameter(name="limit", description="Max results (default: 100)", type=int),
            OpenApiParameter(
                name="offset", description="Offset for pagination (default: 0)", type=int
            ),
            OpenApiParameter(name="contact_id", description="Filter by contact ID", type=str),
            OpenApiParameter(
                name="date_from", description="Filter by start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(
                name="date_to", description="Filter by end date (YYYY-MM-DD)", type=str
            ),
        ],
    )
    def get(self, request):
        limit = get_safe_int_param(request, "limit", default=100, min_val=1, max_val=1000)
        offset = get_safe_int_param(request, "offset", default=0, min_val=0, max_val=100000)
        contact_id = request.query_params.get("contact_id")

        dates, err = validate_date_params(request)
        if err:
            return err
        date_from, date_to = dates["date_from"], dates["date_to"]

        return Response(
            get_transactions(
                request.user,
                limit=limit,
                offset=offset,
                contact_id=contact_id,
                date_from=date_from,
                date_to=date_to,
            )
        )


# Admin Analytics Views (Phase 13)


class DashboardOverviewView(APIView):
    """
    GET: Admin dashboard overview with cross-user aggregated stats.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get dashboard overview (admin only)",
        description="Cross-user aggregation for admin dashboard: total contacts, active journals, stalled count, conversion rate, donation summary.",
        parameters=[
            OpenApiParameter(
                name="date_from", description="Filter start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(name="date_to", description="Filter end date (YYYY-MM-DD)", type=str),
        ],
        responses={200: DashboardOverviewSerializer},
    )
    def get(self, request):
        _, err = validate_date_params(request)
        if err:
            return err
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        data = get_dashboard_overview(date_from=date_from, date_to=date_to)
        serializer = DashboardOverviewSerializer(data)
        return Response(serializer.data)


class StalledContactsView(APIView):
    """
    GET: Get contacts with last journal activity >14 days ago.
    Admin-only endpoint with pagination and sorting.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get stalled contacts (admin only)",
        parameters=[
            OpenApiParameter(name="limit", description="Max results (default: 50)", type=int),
            OpenApiParameter(
                name="offset", description="Offset for pagination (default: 0)", type=int
            ),
            OpenApiParameter(
                name="sort_by",
                description="Sort field (days_stalled, full_name, owner_name, last_activity_date)",
                type=str,
            ),
            OpenApiParameter(name="sort_dir", description="Sort direction (asc, desc)", type=str),
            OpenApiParameter(
                name="date_from", description="Filter start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(name="date_to", description="Filter end date (YYYY-MM-DD)", type=str),
        ],
        responses={200: StalledContactsResponseSerializer},
    )
    def get(self, request):
        limit = get_safe_int_param(request, "limit", default=50, min_val=1, max_val=100)
        offset = get_safe_int_param(request, "offset", default=0, min_val=0, max_val=100000)

        # Parse and validate sort parameters
        sort_by = request.query_params.get("sort_by", "days_stalled")
        sort_dir = request.query_params.get("sort_dir", "desc")

        # Validate sort_by against allowed values
        if sort_by not in ("days_stalled", "full_name", "owner_name", "last_activity_date"):
            sort_by = "days_stalled"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"

        # Validate date parameters
        _, err = validate_date_params(request)
        if err:
            return err
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        data = get_stalled_contacts(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
        )
        serializer = StalledContactsResponseSerializer(data)
        return Response(serializer.data)


class UserPerformanceView(APIView):
    """
    GET: Per-missionary performance metrics.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get user performance metrics (admin only)",
        description="Per-missionary: total contacts, active journals, decisions logged, donation totals.",
        responses={200: UserPerformanceResponseSerializer},
    )
    def get(self, request):
        data = get_user_performance()
        serializer = UserPerformanceResponseSerializer(data)
        return Response(serializer.data)


class SingleUserPerformanceView(APIView):
    """
    GET: Performance metrics for one user.
    Admin-only endpoint. Used by the UserDetail page so we don't fetch the
    entire org to render a single row.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get one user's performance metrics (admin only)",
    )
    def get(self, request, user_id):
        data = get_single_user_performance(user_id)
        if data is None:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)


class ConversionFunnelView(APIView):
    """
    GET: Pipeline stage distribution across all missionaries.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get conversion funnel (admin only)",
        description="Pipeline stage distribution with counts and percentages using Journal 6-stage pipeline.",
        parameters=[
            OpenApiParameter(
                name="date_from", description="Filter start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(name="date_to", description="Filter end date (YYYY-MM-DD)", type=str),
        ],
        responses={200: ConversionFunnelResponseSerializer},
    )
    def get(self, request):
        # Validate date parameters
        _, err = validate_date_params(request)
        if err:
            return err
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        data = get_conversion_funnel(date_from=date_from, date_to=date_to)
        serializer = ConversionFunnelResponseSerializer(data)
        return Response(serializer.data)


class TeamActivityView(APIView):
    """
    GET: Recent activity across all users.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get team activity (admin only)",
        parameters=[
            OpenApiParameter(name="limit", description="Max results (default: 50)", type=int),
            OpenApiParameter(
                name="date_from", description="Filter start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(name="date_to", description="Filter end date (YYYY-MM-DD)", type=str),
        ],
        responses={200: TeamActivityResponseSerializer},
    )
    def get(self, request):
        limit = get_safe_int_param(request, "limit", default=50, min_val=1, max_val=200)

        # Validate date parameters
        _, err = validate_date_params(request)
        if err:
            return err
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        data = get_team_activity(limit=limit, date_from=date_from, date_to=date_to)
        serializer = TeamActivityResponseSerializer(data)
        return Response(serializer.data)


class TeamTrendsView(APIView):
    """
    GET: Team activity trends over past N weeks.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get team trends (admin only)",
        description="Weekly aggregated metrics: decisions logged, donations received, stage progressions.",
        parameters=[
            OpenApiParameter(
                name="weeks", description="Number of weeks (default: 12, min: 1, max: 52)", type=int
            ),
            OpenApiParameter(
                name="date_from", description="Filter start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(name="date_to", description="Filter end date (YYYY-MM-DD)", type=str),
        ],
        responses={200: TeamTrendsResponseSerializer},
    )
    def get(self, request):
        weeks = get_safe_int_param(request, "weeks", default=12, min_val=1, max_val=52)

        # Validate date parameters
        _, err = validate_date_params(request)
        if err:
            return err
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        data = get_team_trends(weeks=weeks, date_from=date_from, date_to=date_to)
        serializer = TeamTrendsResponseSerializer(data)
        return Response(serializer.data)


class UserTrendsView(APIView):
    """
    GET: User activity trends over past N weeks for a specific user.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get user trends (admin only)",
        description="Weekly aggregated metrics for a specific user: decisions logged, donations received, stage progressions.",
        parameters=[
            OpenApiParameter(
                name="user_id", description="User ID (required)", type=str, required=True
            ),
            OpenApiParameter(
                name="weeks", description="Number of weeks (default: 12, min: 1, max: 52)", type=int
            ),
        ],
        responses={200: UserTrendsResponseSerializer},
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id parameter is required"}, status=400)

        weeks = get_safe_int_param(request, "weeks", default=12, min_val=1, max_val=52)
        data = get_user_trends(user_id=user_id, weeks=weeks)
        serializer = UserTrendsResponseSerializer(data)
        return Response(serializer.data)


class UserJournalsView(APIView):
    """
    GET: User journals with progress indicators for a specific user.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get user journals (admin only)",
        description="Journal list with member count, decision count, and active member count for a specific user.",
        parameters=[
            OpenApiParameter(
                name="user_id", description="User ID (required)", type=str, required=True
            ),
        ],
        responses={200: UserJournalsResponseSerializer},
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id parameter is required"}, status=400)

        data = get_user_journals(user_id=user_id)
        serializer = UserJournalsResponseSerializer(data)
        return Response(serializer.data)


class StageContactsView(APIView):
    """
    GET: Get contacts currently in a given pipeline stage.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get stage contacts (admin only)",
        description='Contacts currently in a specific pipeline stage. Pass stage parameter (contact, meet, close, decision, thank, next_steps) or "none" for no activity.',
        parameters=[
            OpenApiParameter(
                name="stage", description="Pipeline stage (required)", type=str, required=True
            ),
            OpenApiParameter(
                name="limit", description="Max results (default: 100, min: 1, max: 500)", type=int
            ),
        ],
        responses={200: StageContactsResponseSerializer},
    )
    def get(self, request):
        stage = request.query_params.get("stage")
        if stage is None:
            return Response({"detail": "stage parameter is required"}, status=400)

        # Handle special value "none" for null stage (No Activity contacts)
        if stage == "none" or stage == "":
            stage = None

        limit = get_safe_int_param(request, "limit", default=100, min_val=1, max_val=500)

        data = get_stage_contacts(stage=stage, limit=limit)
        serializer = StageContactsResponseSerializer(data)
        return Response(serializer.data)


class UserDrilldownView(APIView):
    """
    GET: Get combined summary for quick user inspection (user drilldown panel).
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Get user drilldown (admin only)",
        description="Combined user summary with key stats, stalled count, and recent journals for quick inspection.",
        parameters=[
            OpenApiParameter(
                name="user_id", description="User ID (required)", type=str, required=True
            ),
        ],
        responses={200: UserDrilldownResponseSerializer},
    )
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id parameter is required"}, status=400)

        data = get_user_drilldown(user_id=user_id)

        # Check if service returned an error (user not found)
        if "detail" in data:
            return Response(data, status=404)

        serializer = UserDrilldownResponseSerializer(data)
        return Response(serializer.data)


# Admin Analytics Redesign (Issue #49)


class OrgSettingsView(APIView):
    """
    GET / PATCH the singleton OrgSettings row.
    Admin-only. Powers the org-wide annual goal field on the Settings page.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(tags=["insights"], summary="Get org settings (admin only)")
    def get(self, request):
        # GET is read-only: no get_or_create. If the row doesn't exist yet
        # we report defaults rather than spending a write to materialize it.
        annual_goal_cents = (
            OrgSettings.objects.values_list("annual_goal_cents", flat=True).first() or 0
        )
        return Response(OrgSettingsSerializer({"annual_goal_cents": annual_goal_cents}).data)

    @extend_schema(tags=["insights"], summary="Update org settings (admin only)")
    def patch(self, request):
        serializer = OrgSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Wrap the singleton materialise + write in a transaction with a row
        # lock so two concurrent first-PATCH requests don't race on
        # get_or_create. Once the row exists this is just a normal locked
        # update; the lock cost is bounded by how long the write takes.
        with transaction.atomic():
            OrgSettings.get_solo()  # ensure row exists before locking it
            instance = OrgSettings.objects.select_for_update().get(pk=OrgSettings._solo_uuid())
            if "annual_goal_cents" in serializer.validated_data:
                instance.annual_goal_cents = serializer.validated_data["annual_goal_cents"]
                instance.save(update_fields=["annual_goal_cents", "updated_at"])

        return Response(
            OrgSettingsSerializer({"annual_goal_cents": instance.annual_goal_cents}).data
        )


class FiscalYearPaceView(APIView):
    """GET: Hero pace tile — raised vs annual goal, YoY delta, last import."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Fiscal year pace (admin only)",
        responses={200: FiscalYearPaceResponseSerializer},
    )
    def get(self, request):
        return Response(get_fiscal_year_pace(request))


class MissionariesBehindGoalView(APIView):
    """GET: Missionaries sorted ascending by this-month pace %."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Missionaries behind goal (admin only)",
        parameters=[
            OpenApiParameter(
                name="limit", description="Max results (default: 10, max: 50)", type=int
            ),
        ],
        responses={200: MissionariesBehindGoalResponseSerializer},
    )
    def get(self, request):
        limit = get_safe_int_param(request, "limit", default=10, min_val=1, max_val=50)
        return Response(get_missionaries_behind_goal(request, limit=limit))


class PipelineFunnelConversionView(APIView):
    """GET: Stage-to-stage conversion funnel with weakest-transition flag."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Pipeline funnel with conversion (admin only)",
        responses={200: PipelineFunnelConversionResponseSerializer},
    )
    def get(self, request):
        return Response(get_pipeline_funnel_with_conversion(request))


class WeeklyEngagementView(APIView):
    """GET: Weekly active + on-pace missionary counts over a rolling window."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Weekly engagement (admin only)",
        parameters=[
            OpenApiParameter(
                name="weeks", description="Lookback window (default: 12, max: 52)", type=int
            ),
        ],
        responses={200: WeeklyEngagementResponseSerializer},
    )
    def get(self, request):
        weeks = get_safe_int_param(request, "weeks", default=12, min_val=1, max_val=52)
        return Response(get_weekly_engagement(request, weeks=weeks))


class FiscalYearDonationsView(APIView):
    """GET: Monthly FYTD donation totals vs prior year."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Fiscal year donations vs prior year (admin only)",
        responses={200: FiscalYearDonationsResponseSerializer},
    )
    def get(self, request):
        return Response(get_fiscal_year_donations(request))
