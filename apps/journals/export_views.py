"""
CSV export view for journals with FilterSet-based filtering.
"""

from datetime import datetime

from django.http import StreamingHttpResponse

from rest_framework import permissions
from rest_framework.views import APIView

from apps.core.csv_export import safe_csv_stream
from apps.core.permissions import get_visible_user_ids, is_financial_role
from apps.imports.services import sanitize_csv_value
from apps.journals.filters import JournalFilterSet
from apps.journals.models import Journal


class JournalExportCSVView(APIView):
    """
    GET: Export journals as filtered CSV file.
    Applies the same JournalFilterSet as the list endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Same owner-scoping as JournalListCreateView
        visible = get_visible_user_ids(user, request=request)
        queryset = Journal.objects.filter(owner_id__in=visible)

        # Exclude archived by default unless is_archived filter present
        if "is_archived" not in request.query_params:
            queryset = queryset.filter(is_archived=False)

        # Apply FilterSet (same as list endpoint)
        filterset = JournalFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related("owner")[:10000]

        # Goal Amount is financial detail — blanked for non-financial requesters
        # (coach) so the export cannot leak coached-user goals (CWE-200; re-scan
        # #3). The column stays in the header so the CSV shape is stable.
        include_goal = is_financial_role(user)

        filename = f"journals_{datetime.now().date().isoformat()}.csv"

        def generate_rows(writer):
            # Header
            yield writer.writerow(
                [
                    "Name",
                    "Goal Amount",
                    "Deadline",
                    "Archived",
                    "Owner",
                    "Created",
                ]
            )

            # Data rows
            for journal in filtered_qs:
                owner_name = ""
                if journal.owner:
                    owner_name = journal.owner.full_name

                yield writer.writerow(
                    [
                        sanitize_csv_value(journal.name),
                        str(journal.goal_amount or 0) if include_goal else "",
                        journal.deadline or "",
                        "Yes" if journal.is_archived else "No",
                        sanitize_csv_value(owner_name),
                        journal.created_at.date().isoformat() if journal.created_at else "",
                    ]
                )

        response = StreamingHttpResponse(
            safe_csv_stream(generate_rows, export_name="journals"), content_type="text/csv"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
