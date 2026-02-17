"""
CSV export view for pledges with FilterSet-based filtering.
"""
import csv
from datetime import datetime

from rest_framework import permissions
from rest_framework.views import APIView
from django.http import StreamingHttpResponse

from apps.imports.services import sanitize_csv_value
from apps.pledges.filters import PledgeFilterSet
from apps.pledges.models import Pledge


class Echo:
    """Pseudo-buffer for csv.writer to write to StreamingHttpResponse."""
    def write(self, value):
        return value


class PledgeExportCSVView(APIView):
    """
    GET: Export pledges as filtered CSV file.
    Applies the same PledgeFilterSet as the list endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Same owner-scoping as PledgeListCreateView
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Pledge.objects.all()
        else:
            queryset = Pledge.objects.filter(contact__owner=user)

        # Apply FilterSet (same as list endpoint)
        filterset = PledgeFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related('contact')[:10000]

        filename = f'pledges_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

            # Header
            yield writer.writerow([
                'Contact',
                'Amount',
                'Frequency',
                'Status',
                'Start Date',
                'Is Late',
                'Total Received',
            ])

            # Data rows
            for pledge in filtered_qs:
                contact_name = ''
                if pledge.contact:
                    contact_name = f'{pledge.contact.first_name} {pledge.contact.last_name}'

                yield writer.writerow([
                    sanitize_csv_value(contact_name),
                    str(pledge.amount or 0),
                    sanitize_csv_value(pledge.frequency or ''),
                    sanitize_csv_value(pledge.status or ''),
                    pledge.start_date or '',
                    'Yes' if pledge.is_late else 'No',
                    str(pledge.total_received or 0),
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
