"""
CSV export view for contacts with FilterSet-based filtering.
"""
import csv
from datetime import datetime

from rest_framework import permissions
from rest_framework.views import APIView
from django.http import StreamingHttpResponse

from apps.contacts.filters import ContactFilterSet
from apps.contacts.models import Contact
from apps.core.permissions import get_visible_user_ids
from apps.imports.services import sanitize_csv_value


class Echo:
    """Pseudo-buffer for csv.writer to write to StreamingHttpResponse."""
    def write(self, value):
        return value


class ContactExportCSVView(APIView):
    """
    GET: Export contacts as filtered CSV file.
    Applies the same ContactFilterSet as the list endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Same owner-scoping as ContactListCreateView
        visible = get_visible_user_ids(user)
        if visible is None:
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner_id__in=visible)

        # Admin/supervisor/coach owner filter (intentionally NOT in FilterSet - security)
        owner_id = request.query_params.get('owner')
        if owner_id and user.role in ['admin', 'supervisor', 'coach']:
            if visible is None or int(owner_id) in visible:
                queryset = queryset.filter(owner_id=owner_id)

        # Apply FilterSet (same as list endpoint)
        filterset = ContactFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related('owner')[:10000]

        filename = f'contacts_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

            # Header
            yield writer.writerow([
                'Name',
                'Email',
                'Phone',
                'Status',
                'Owner',
                'Last Gift Date',
                'Total Given',
            ])

            # Data rows
            for contact in filtered_qs:
                yield writer.writerow([
                    sanitize_csv_value(f'{contact.first_name} {contact.last_name}'),
                    sanitize_csv_value(contact.email or ''),
                    sanitize_csv_value(contact.phone or ''),
                    sanitize_csv_value(contact.status or ''),
                    sanitize_csv_value(contact.owner.full_name if contact.owner else ''),
                    contact.last_gift_date or '',
                    str(contact.total_given or 0),
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
