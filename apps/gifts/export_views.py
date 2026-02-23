"""
CSV export views for Gift and RecurringGift with FilterSet-based filtering.
"""
import csv
from datetime import datetime

from django.http import StreamingHttpResponse
from rest_framework import permissions
from rest_framework.views import APIView

from apps.gifts.filters import GiftFilterSet, RecurringGiftFilterSet
from apps.gifts.models import Gift, RecurringGift
from apps.imports.services import sanitize_csv_value


class Echo:
    """Pseudo-buffer for csv.writer to write to StreamingHttpResponse."""
    def write(self, value):
        return value


class GiftExportCSVView(APIView):
    """
    GET: Export gifts as filtered CSV file.
    Applies the same GiftFilterSet as the list endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Same owner-scoping as GiftListCreateView
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = Gift.objects.all()
        else:
            queryset = Gift.objects.filter(donor_contact__owner=user)

        # Admin-only owner filter
        owner_id = request.query_params.get('owner')
        if owner_id and user.role == 'admin':
            queryset = queryset.filter(donor_contact__owner_id=owner_id)

        # Apply FilterSet (same as list endpoint)
        filterset = GiftFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related('donor_contact', 'fund')[:10000]

        filename = f'donations_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

            # Header
            yield writer.writerow([
                'Donor Name',
                'Amount',
                'Date',
                'Fund',
                'Description',
            ])

            # Data rows
            for gift in filtered_qs:
                yield writer.writerow([
                    sanitize_csv_value(gift.donor_contact.full_name),
                    str(gift.amount_dollars),
                    gift.gift_date.isoformat(),
                    sanitize_csv_value(gift.fund.name if gift.fund else ''),
                    sanitize_csv_value(gift.description or ''),
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class RecurringGiftExportCSVView(APIView):
    """
    GET: Export recurring gifts as filtered CSV file.
    Applies the same RecurringGiftFilterSet as the list endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Same owner-scoping as RecurringGiftListCreateView
        if user.role in ['admin', 'finance', 'read_only']:
            queryset = RecurringGift.objects.all()
        else:
            queryset = RecurringGift.objects.filter(donor_contact__owner=user)

        # Admin-only owner filter
        owner_id = request.query_params.get('owner')
        if owner_id and user.role == 'admin':
            queryset = queryset.filter(donor_contact__owner_id=owner_id)

        # Apply FilterSet (same as list endpoint)
        filterset = RecurringGiftFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related('donor_contact', 'fund')[:10000]

        filename = f'pledges_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

            # Header
            yield writer.writerow([
                'Donor Name',
                'Amount',
                'Frequency',
                'Status',
                'Start Date',
                'Fund',
            ])

            # Data rows
            for rg in filtered_qs:
                yield writer.writerow([
                    sanitize_csv_value(rg.donor_contact.full_name),
                    str(rg.amount_dollars),
                    rg.frequency,
                    rg.status,
                    rg.start_date.isoformat(),
                    sanitize_csv_value(rg.fund.name if rg.fund else ''),
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
