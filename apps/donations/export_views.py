"""
CSV export view for donations with FilterSet-based filtering.
"""
import csv
from datetime import datetime

from rest_framework import permissions
from rest_framework.views import APIView
from django.http import StreamingHttpResponse

from apps.donations.filters import DonationFilterSet
from apps.donations.models import Donation
from apps.imports.services import sanitize_csv_value


class Echo:
    """Pseudo-buffer for csv.writer to write to StreamingHttpResponse."""
    def write(self, value):
        return value


class DonationExportCSVView(APIView):
    """
    GET: Export donations as filtered CSV file.
    Applies the same DonationFilterSet as the list endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Same owner-scoping as DonationListCreateView
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Donation.objects.all()
        else:
            queryset = Donation.objects.filter(contact__owner=user)

        # Apply FilterSet (same as list endpoint)
        filterset = DonationFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related('contact', 'pledge')[:10000]

        filename = f'donations_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

            # Header
            yield writer.writerow([
                'Date',
                'Contact',
                'Amount',
                'Type',
                'Payment Method',
                'Thanked',
                'Pledge',
            ])

            # Data rows
            for donation in filtered_qs:
                contact_name = ''
                if donation.contact:
                    contact_name = f'{donation.contact.first_name} {donation.contact.last_name}'

                yield writer.writerow([
                    donation.date or '',
                    sanitize_csv_value(contact_name),
                    str(donation.amount or 0),
                    sanitize_csv_value(donation.donation_type or ''),
                    sanitize_csv_value(donation.payment_method or ''),
                    'Yes' if donation.thanked else 'No',
                    str(donation.pledge_id or ''),
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
