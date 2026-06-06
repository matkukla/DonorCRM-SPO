"""
CSV export view for journals with FilterSet-based filtering.
"""

import csv
from datetime import datetime

from django.http import StreamingHttpResponse

from rest_framework import permissions
from rest_framework.views import APIView

from apps.core.permissions import get_visible_user_ids
from apps.imports.services import sanitize_csv_value
from apps.journals.filters import JournalFilterSet
from apps.journals.models import Journal


class Echo:
    """Pseudo-buffer for csv.writer to write to StreamingHttpResponse."""

    def write(self, value):
        return value


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

        filename = f"journals_{datetime.now().date().isoformat()}.csv"

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

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
                        str(journal.goal_amount or 0),
                        journal.deadline or "",
                        "Yes" if journal.is_archived else "No",
                        sanitize_csv_value(owner_name),
                        journal.created_at.date().isoformat() if journal.created_at else "",
                    ]
                )

        response = StreamingHttpResponse(generate_csv(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
