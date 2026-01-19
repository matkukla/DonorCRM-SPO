"""
Views for CSV import/export.
"""
import logging
import uuid

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdmin, IsFinanceOrAdmin
from apps.imports.services import (
    export_contacts_csv,
    export_donations_csv,
    get_contacts_template,
    get_donations_template,
    import_contacts,
    import_donations,
    parse_contacts_csv,
    parse_donations_csv,
)
from apps.imports.tasks import (
    get_import_progress,
    import_contacts_async,
    import_donations_async,
)

logger = logging.getLogger(__name__)

# Threshold for using async import (number of rows)
ASYNC_THRESHOLD = 50


class ContactImportView(APIView):
    """
    POST: Import contacts from CSV file (admin only)

    Query params:
        validate_only: If 'true', only validate without importing
        async: If 'true', process import asynchronously (recommended for large files)
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response(
                {'detail': 'File must be a CSV.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Read and decode file content
        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response(
                {'detail': 'File encoding error. Please use UTF-8.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f'Contact import started by user {request.user.email}')

        # Parse CSV
        valid_records, errors = parse_contacts_csv(content, request.user)

        # Option to just validate (dry run)
        if request.query_params.get('validate_only') == 'true':
            return Response({
                'valid_count': len(valid_records),
                'error_count': len(errors),
                'errors': errors[:20]  # Limit errors in response
            })

        # Use async import for large files
        use_async = (
            request.query_params.get('async') == 'true' or
            len(valid_records) > ASYNC_THRESHOLD
        )

        if use_async and valid_records:
            import_id = uuid.uuid4().hex[:12]
            import_contacts_async.delay(content, request.user.id, import_id)
            logger.info(f'Contact import {import_id} queued for async processing')
            return Response({
                'status': 'processing',
                'import_id': import_id,
                'message': f'{len(valid_records)} contacts queued for import',
                'error_count': len(errors),
                'errors': errors[:20]
            }, status=status.HTTP_202_ACCEPTED)

        # Sync import for small files
        if valid_records:
            count, contacts = import_contacts(valid_records, request.user)
        else:
            count = 0

        logger.info(f'Contact import completed: {count} contacts imported')

        return Response({
            'imported_count': count,
            'error_count': len(errors),
            'errors': errors[:20]
        })


class DonationImportView(APIView):
    """
    POST: Import donations from CSV file (admin/finance only)

    Query params:
        validate_only: If 'true', only validate without importing
        async: If 'true', process import asynchronously (recommended for large files)
    """
    permission_classes = [permissions.IsAuthenticated, IsFinanceOrAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return Response(
                {'detail': 'File must be a CSV.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Read and decode file content
        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response(
                {'detail': 'File encoding error. Please use UTF-8.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f'Donation import started by user {request.user.email}')

        # Parse CSV
        valid_records, errors = parse_donations_csv(content, request.user)

        # Option to just validate (dry run)
        if request.query_params.get('validate_only') == 'true':
            return Response({
                'valid_count': len(valid_records),
                'error_count': len(errors),
                'errors': errors[:20]
            })

        # Use async import for large files
        use_async = (
            request.query_params.get('async') == 'true' or
            len(valid_records) > ASYNC_THRESHOLD
        )

        if use_async and valid_records:
            import_id = uuid.uuid4().hex[:12]
            import_donations_async.delay(content, request.user.id, import_id)
            logger.info(f'Donation import {import_id} queued for async processing')
            return Response({
                'status': 'processing',
                'import_id': import_id,
                'message': f'{len(valid_records)} donations queued for import',
                'error_count': len(errors),
                'errors': errors[:20]
            }, status=status.HTTP_202_ACCEPTED)

        # Sync import for small files
        if valid_records:
            count, donations = import_donations(valid_records)
        else:
            count = 0

        logger.info(f'Donation import completed: {count} donations imported')

        return Response({
            'imported_count': count,
            'error_count': len(errors),
            'errors': errors[:20]
        })


class ContactExportView(APIView):
    """
    GET: Export contacts to CSV
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.contacts.models import Contact

        user = request.user
        if user.role == 'admin':
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(owner=user)

        csv_content = export_contacts_csv(queryset)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contacts.csv"'
        return response


class DonationExportView(APIView):
    """
    GET: Export donations to CSV
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.donations.models import Donation

        user = request.user
        if user.role in ['admin', 'finance']:
            queryset = Donation.objects.all()
        else:
            queryset = Donation.objects.filter(contact__owner=user)

        # Date range filter
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        csv_content = export_donations_csv(queryset)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="donations.csv"'
        return response


class ContactTemplateView(APIView):
    """
    GET: Download contacts CSV template
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        content = get_contacts_template()
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contacts_template.csv"'
        return response


class DonationTemplateView(APIView):
    """
    GET: Download donations CSV template
    """
    permission_classes = [permissions.IsAuthenticated, IsFinanceOrAdmin]

    def get(self, request):
        content = get_donations_template()
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="donations_template.csv"'
        return response


class ImportStatusView(APIView):
    """
    GET: Check status of an async import
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, import_id):
        progress = get_import_progress(import_id)
        return Response(progress)
