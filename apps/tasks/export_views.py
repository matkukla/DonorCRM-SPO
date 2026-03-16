"""
CSV export view for tasks with FilterSet-based filtering.
"""
import csv
from datetime import datetime

from rest_framework import permissions
from rest_framework.views import APIView
from django.http import StreamingHttpResponse

from apps.core.permissions import get_visible_user_ids
from apps.imports.services import sanitize_csv_value
from apps.tasks.filters import TaskFilterSet
from apps.tasks.models import Task


class Echo:
    """Pseudo-buffer for csv.writer to write to StreamingHttpResponse."""
    def write(self, value):
        return value


class TaskExportCSVView(APIView):
    """
    GET: Export tasks as filtered CSV file.
    Applies the same TaskFilterSet as the list endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Same owner-scoping as TaskListCreateView
        visible = get_visible_user_ids(user, request=request)
        if visible is None:
            queryset = Task.objects.all()
        else:
            queryset = Task.objects.filter(owner_id__in=visible)

        # Apply FilterSet (same as list endpoint)
        filterset = TaskFilterSet(request.query_params, queryset=queryset)
        filtered_qs = filterset.qs.select_related('owner', 'contact')[:10000]

        filename = f'tasks_{datetime.now().date().isoformat()}.csv'

        def generate_csv():
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)

            # Header
            yield writer.writerow([
                'Title',
                'Contact',
                'Status',
                'Priority',
                'Type',
                'Due Date',
                'Created At',
            ])

            # Data rows
            for task in filtered_qs:
                contact_name = ''
                if task.contact:
                    contact_name = f'{task.contact.first_name} {task.contact.last_name}'

                yield writer.writerow([
                    sanitize_csv_value(task.title or ''),
                    sanitize_csv_value(contact_name),
                    sanitize_csv_value(task.status or ''),
                    sanitize_csv_value(task.priority or ''),
                    sanitize_csv_value(task.task_type or ''),
                    task.due_date or '',
                    task.created_at.isoformat() if task.created_at else '',
                ])

        response = StreamingHttpResponse(generate_csv(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
