"""
CSV export views for admin analytics endpoints.
"""

from datetime import datetime

from django.http import StreamingHttpResponse

from rest_framework import permissions
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.core.csv_export import safe_csv_stream as _safe_csv_stream
from apps.core.permissions import IsAdmin
from apps.core.utils import get_safe_int_param, validate_date_params
from apps.imports.services import sanitize_csv_value
from apps.insights.services import get_stalled_contacts, get_team_activity


class StalledContactsCSVView(APIView):
    """
    GET: Export stalled contacts as CSV file.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Export stalled contacts CSV (admin only)",
        parameters=[
            OpenApiParameter(
                name="date_from", description="Filter start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(name="date_to", description="Filter end date (YYYY-MM-DD)", type=str),
            OpenApiParameter(
                name="sort_by",
                description="Sort field (days_stalled, full_name, owner_name, last_activity_date)",
                type=str,
            ),
            OpenApiParameter(name="sort_dir", description="Sort direction (asc, desc)", type=str),
        ],
    )
    def get(self, request):
        # Parse query parameters
        _, err = validate_date_params(request)
        if err:
            return err
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        sort_by = request.query_params.get("sort_by", "days_stalled")
        sort_dir = request.query_params.get("sort_dir", "desc")

        # Validate sort parameters
        if sort_by not in ("days_stalled", "full_name", "owner_name", "last_activity_date"):
            sort_by = "days_stalled"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"

        # Get all stalled contacts (no limit)
        data = get_stalled_contacts(
            limit=None,
            offset=0,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
        )

        # Build filename with date range
        if date_from and date_to:
            filename = f"stalled_contacts_{date_from}_to_{date_to}.csv"
        elif date_from:
            filename = f"stalled_contacts_from_{date_from}.csv"
        elif date_to:
            filename = f"stalled_contacts_to_{date_to}.csv"
        else:
            filename = f"stalled_contacts_{datetime.now().date().isoformat()}.csv"

        def rows(writer):
            yield writer.writerow(
                [
                    "Contact Name",
                    "Email",
                    "Owner",
                    "Last Activity Date",
                    "Days Stalled",
                    "Status",
                ]
            )
            for contact in data["stalled_contacts"]:
                yield writer.writerow(
                    [
                        sanitize_csv_value(contact["full_name"]),
                        sanitize_csv_value(contact["email"] or ""),
                        sanitize_csv_value(contact["owner_name"]),
                        contact["last_activity_date"] or "",
                        contact["days_stalled"] or "",
                        sanitize_csv_value(contact["status"]),
                    ]
                )

        response = StreamingHttpResponse(
            _safe_csv_stream(rows, export_name="stalled_contacts"),
            content_type="text/csv",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class TeamActivityCSVView(APIView):
    """
    GET: Export team activity as CSV file.
    Admin-only endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["insights"],
        summary="Export team activity CSV (admin only)",
        parameters=[
            OpenApiParameter(
                name="date_from", description="Filter start date (YYYY-MM-DD)", type=str
            ),
            OpenApiParameter(name="date_to", description="Filter end date (YYYY-MM-DD)", type=str),
            OpenApiParameter(name="limit", description="Max results (default: 10000)", type=int),
        ],
    )
    def get(self, request):
        # Parse query parameters
        _, err = validate_date_params(request)
        if err:
            return err
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        limit = get_safe_int_param(request, "limit", default=10000, min_val=1, max_val=100000)

        # Get team activity with high limit for export
        data = get_team_activity(limit=limit, date_from=date_from, date_to=date_to)

        # Build filename with date range
        if date_from and date_to:
            filename = f"team_activity_{date_from}_to_{date_to}.csv"
        elif date_from:
            filename = f"team_activity_from_{date_from}.csv"
        elif date_to:
            filename = f"team_activity_to_{date_to}.csv"
        else:
            filename = f"team_activity_{datetime.now().date().isoformat()}.csv"

        def rows(writer):
            yield writer.writerow(
                [
                    "Date",
                    "User",
                    "Event Type",
                    "Title",
                    "Contact Name",
                ]
            )
            for activity in data["activities"]:
                yield writer.writerow(
                    [
                        activity["created_at"],
                        sanitize_csv_value(activity["user_name"]),
                        sanitize_csv_value(activity["event_type"]),
                        sanitize_csv_value(activity["title"]),
                        sanitize_csv_value(activity["contact_name"] or ""),
                    ]
                )

        response = StreamingHttpResponse(
            _safe_csv_stream(rows, export_name="team_activity"),
            content_type="text/csv",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
