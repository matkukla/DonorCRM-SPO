"""
Views for CSV import/export.
"""
import csv
import io
import logging
import uuid

from django.http import HttpResponse

from rest_framework import generics, permissions, serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdmin, IsStaffOrAbove
from apps.imports.generic_services import (
    VALID_MATCH_BY,
    import_generic_contacts,
    import_generic_donations,
)
from apps.imports.models import Fund, ImportBatchStatus, MPDSnapshot, MPDUpload
from apps.imports.mpd_services import process_mpd_upload
from apps.imports.re_services import (
    import_re_constituents,
    import_re_gifts,
    import_re_recurring_gifts,
    import_re_solicitors,
)
from apps.imports.services import (
    export_contacts_csv,
    export_gifts_csv,
    get_contacts_template,
    get_entities_template,
    get_funds_template,
    import_contacts,
    import_entities,
    import_funds,
    parse_contacts_csv,
    parse_entities_csv,
    parse_funds_csv,
)
from apps.imports.spo_services import import_spo_gifts, import_spo_prayers, reconcile_missionaries
from apps.imports.tasks import get_import_progress, import_contacts_async

logger = logging.getLogger(__name__)

# File upload size limit (10 MB)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

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
        if "file" not in request.FILES:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not file.name.endswith(".csv"):
            return Response({"detail": "File must be a CSV."}, status=status.HTTP_400_BAD_REQUEST)

        # Read and decode file content
        try:
            content = file.read().decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"detail": "File encoding error. Please use UTF-8."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Contact import started by user {request.user.email}")

        # Parse CSV
        valid_records, errors = parse_contacts_csv(content, request.user)

        # Option to just validate (dry run)
        if request.query_params.get("validate_only") == "true":
            return Response(
                {
                    "valid_count": len(valid_records),
                    "error_count": len(errors),
                    "errors": errors[:20],  # Limit errors in response
                }
            )

        # Use async import for large files
        use_async = (
            request.query_params.get("async") == "true" or len(valid_records) > ASYNC_THRESHOLD
        )

        if use_async and valid_records:
            import_id = uuid.uuid4().hex[:12]
            import_contacts_async.delay(content, request.user.id, import_id)
            logger.info(f"Contact import {import_id} queued for async processing")
            return Response(
                {
                    "status": "processing",
                    "import_id": import_id,
                    "message": f"{len(valid_records)} contacts queued for import",
                    "error_count": len(errors),
                    "errors": errors[:20],
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Sync import for small files
        if valid_records:
            count, contacts = import_contacts(valid_records, request.user)
        else:
            count = 0

        logger.info(f"Contact import completed: {count} contacts imported")

        return Response(
            {"imported_count": count, "error_count": len(errors), "errors": errors[:20]}
        )


class DonationImportView(APIView):
    """
    POST: Legacy donation import endpoint.
    Superseded by RE Gift import (REGiftImportView).
    Returns 410 Gone to direct users to the new import endpoint.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request):
        return Response(
            {
                "detail": "Legacy donation import has been removed. Use the RE Gift import endpoint instead."
            },
            status=status.HTTP_410_GONE,
        )


class ContactExportView(APIView):
    """
    GET: Export contacts to CSV
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.contacts.models import Contact

        user = request.user
        if user.role == "admin":
            queryset = Contact.objects.filter(is_merged=False)
        else:
            queryset = Contact.objects.filter(owner=user, is_merged=False)

        csv_content = export_contacts_csv(queryset)

        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="contacts.csv"'
        return response


class DonationExportView(APIView):
    """
    GET: Export gifts to CSV
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.gifts.models import Gift

        user = request.user
        if user.role in ["admin", "finance"]:
            queryset = Gift.objects.all()
        else:
            queryset = Gift.objects.filter(donor_contact__owner=user)

        # Date range filter
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(gift_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(gift_date__lte=end_date)

        csv_content = export_gifts_csv(queryset)

        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="gifts.csv"'
        return response


class ContactTemplateView(APIView):
    """
    GET: Download contacts CSV template
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        content = get_contacts_template()
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="contacts_template.csv"'
        return response


class DonationTemplateView(APIView):
    """
    GET: Legacy donation template endpoint.
    Superseded by RE Gift import. Returns 410 Gone.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(
            {
                "detail": "Legacy donation template has been removed. Use the RE Gift import instead."
            },
            status=status.HTTP_410_GONE,
        )


class FundImportView(APIView):
    """
    POST: Import funds from CSV file (admin only)

    Query params:
        validate_only: If 'true', only validate without importing
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not file.name.endswith(".csv"):
            return Response({"detail": "File must be a CSV."}, status=status.HTTP_400_BAD_REQUEST)

        # Read and decode file content (utf-8-sig handles Excel BOM)
        try:
            content = file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response(
                {"detail": "File encoding error. Please use UTF-8."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Fund import started by user {request.user.email}")

        # Parse CSV
        valid_records, errors = parse_funds_csv(content)

        # Option to just validate (dry run)
        if request.query_params.get("validate_only") == "true":
            return Response(
                {
                    "valid_count": len(valid_records),
                    "error_count": len(errors),
                    "errors": errors[:20],  # Limit errors in response
                }
            )

        # Create ImportRun audit record
        from apps.imports.models import ImportRun, ImportStatus, ImportType

        import_run = ImportRun.objects.create(
            type=ImportType.FUNDS,
            status=ImportStatus.IMPORTING,
            filename=file.name,
            uploaded_by=request.user,
        )

        # Sync import (MVP - no async)
        if valid_records:
            created_count, updated_count = import_funds(valid_records, import_run)
        else:
            created_count = 0
            updated_count = 0
            import_run.created_count = 0
            import_run.updated_count = 0
            import_run.status = ImportStatus.COMPLETED
            import_run.save()

        logger.info(f"Fund import completed: {created_count} created, {updated_count} updated")

        return Response(
            {
                "created_count": created_count,
                "updated_count": updated_count,
                "error_count": len(errors),
                "errors": errors[:20],
                "import_run_id": import_run.id,
            }
        )


class FundTemplateView(APIView):
    """
    GET: Download funds CSV template
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        content = get_funds_template()
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="funds_template.csv"'
        return response


class EntityImportView(APIView):
    """
    POST: Import entities from CSV file (admin only)

    Query params:
        validate_only: If 'true', only validate without importing
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not file.name.endswith(".csv"):
            return Response({"detail": "File must be a CSV."}, status=status.HTTP_400_BAD_REQUEST)

        # Read and decode file content (utf-8-sig handles Excel BOM)
        try:
            content = file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response(
                {"detail": "File encoding error. Please use UTF-8."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Entity import started by user {request.user.email}")

        # Parse CSV
        valid_records, errors = parse_entities_csv(content, request.user)

        # Option to just validate (dry run)
        if request.query_params.get("validate_only") == "true":
            return Response(
                {
                    "valid_count": len(valid_records),
                    "error_count": len(errors),
                    "errors": errors[:20],  # Limit errors in response
                }
            )

        # Create ImportRun audit record
        from apps.imports.models import ImportRun, ImportStatus, ImportType

        import_run = ImportRun.objects.create(
            type=ImportType.ENTITIES,
            status=ImportStatus.IMPORTING,
            filename=file.name,
            uploaded_by=request.user,
        )

        # Sync import (MVP - no async)
        if valid_records:
            created_count, updated_count = import_entities(valid_records, request.user, import_run)
        else:
            created_count = 0
            updated_count = 0
            import_run.created_count = 0
            import_run.updated_count = 0
            import_run.status = ImportStatus.COMPLETED
            import_run.save()

        logger.info(f"Entity import completed: {created_count} created, {updated_count} updated")

        return Response(
            {
                "created_count": created_count,
                "updated_count": updated_count,
                "error_count": len(errors),
                "errors": errors[:20],
                "import_run_id": import_run.id,
            }
        )


class EntityTemplateView(APIView):
    """
    GET: Download entities CSV template
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        content = get_entities_template()
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="entities_template.csv"'
        return response


class TransactionImportView(APIView):
    """
    POST: Legacy transaction import endpoint.
    Superseded by RE Gift import (REGiftImportView).
    Returns 410 Gone.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request):
        return Response(
            {
                "detail": "Legacy transaction import has been removed. Use the RE Gift import endpoint instead."
            },
            status=status.HTTP_410_GONE,
        )


class TransactionTemplateView(APIView):
    """
    GET: Legacy transaction template endpoint.
    Superseded by RE Gift import. Returns 410 Gone.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(
            {
                "detail": "Legacy transaction template has been removed. Use the RE Gift import instead."
            },
            status=status.HTTP_410_GONE,
        )


class ImportStatusView(APIView):
    """
    GET: Check status of an async import
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, import_id):
        progress = get_import_progress(import_id)
        return Response(progress)


class PledgeImportView(APIView):
    """
    POST: Legacy pledge import endpoint.
    Superseded by RE Recurring Gift import (RERecurringGiftImportView).
    Returns 410 Gone.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request):
        return Response(
            {
                "detail": "Legacy pledge import has been removed. Use the RE Recurring Gift import endpoint instead."
            },
            status=status.HTTP_410_GONE,
        )


class PledgeTemplateView(APIView):
    """
    GET: Legacy pledge template endpoint.
    Superseded by RE Recurring Gift import. Returns 410 Gone.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(
            {
                "detail": "Legacy pledge template has been removed. Use the RE Recurring Gift import instead."
            },
            status=status.HTTP_410_GONE,
        )


class LatestImportRunsView(APIView):
    """
    GET: Fetch latest import run for each type and dependency counts

    Returns the most recent ImportRun for each of the 4 import types
    (funds, entities, transactions, pledges), along with dependency counts
    for showing warnings in the UI.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.contacts.models import Contact
        from apps.imports.models import Fund, ImportRun, ImportType

        latest = {}

        # Get latest run for each import type
        for import_type in ImportType.values:
            run = ImportRun.objects.filter(type=import_type).order_by("-created_at").first()

            if run:
                latest[import_type] = {
                    "id": str(run.id),
                    "status": run.status,
                    "created_at": run.created_at.isoformat(),
                    "created_count": run.created_count,
                    "updated_count": run.updated_count,
                    "error_count": run.error_count,
                }
            else:
                latest[import_type] = None

        # Get dependency counts for UI warnings
        latest["dependency_counts"] = {
            "funds_count": Fund.objects.count(),
            "entities_with_external_id_count": Contact.objects.exclude(external_id="")
            .exclude(external_id__isnull=True)
            .count(),
        }

        return Response(latest)


class ImportRunErrorsCSVView(APIView):
    """
    GET: Download CSV of failed rows for an import run

    Returns CSV file with original row data plus error_message column.
    Used by Import Center to allow admin to fix and re-import failed rows.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request, import_run_id):
        from apps.imports.models import ImportRowError, ImportRun

        try:
            import_run = ImportRun.objects.get(id=import_run_id)
        except ImportRun.DoesNotExist:
            return Response({"detail": "Import run not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all error rows for this import run
        errors = ImportRowError.objects.filter(import_run=import_run).order_by("row_number")

        if not errors.exists():
            return Response(
                {"detail": "No errors found for this import run."}, status=status.HTTP_404_NOT_FOUND
            )

        # Build CSV in memory
        output = io.StringIO()

        # Get headers from first error's row_data, add error_message column
        first_error = errors.first()
        headers = list(first_error.row_data.keys()) + ["error_message"]

        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for error in errors:
            row = dict(error.row_data)
            row["error_message"] = "; ".join(error.error_messages)
            writer.writerow(row)

        # Prepare response
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        filename = f"{import_run.type}_errors_{import_run.id}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# Inline serializer: only 3 lines, not worth a separate serializers module.
class FundListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ["id", "name"]


class FundListView(generics.ListAPIView):
    """
    GET: List all active funds for dropdown selectors.
    Returns [{id, name}] without pagination.
    """

    serializer_class = FundListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Return all funds without pagination

    def get_queryset(self):
        return Fund.objects.filter(status="active").order_by("name")


class MPDImportView(APIView):
    """
    POST: Upload Smartsheet MPD Dashboard Report (admin only).

    Accepts CSV or XLSX file. Auto-detects format from file content.
    Matches each row to a DonorCRM user by First Name + Last Name.
    Creates MPDSnapshot records for matched users.

    Response includes:
    - upload_id: UUID of the MPDUpload record
    - status: 'completed' or 'failed'
    - total_rows: number of data rows in file
    - matched_count: number of rows matched to users
    - unmatched_count: number of rows not matched
    - unmatched_rows: list of {row, first_name, last_name} for unmatched
    - snapshot_count: number of MPDSnapshot records created
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Read raw bytes for format detection (not decoding to string)
        file_bytes = file.read()

        try:
            upload = process_mpd_upload(
                file_bytes=file_bytes,
                filename=file.name,
                uploaded_by=request.user,
            )
        except Exception as e:
            logger.error(f"MPD import failed: {e}")
            return Response(
                {"detail": f"Import failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        response_data = {
            "upload_id": str(upload.id),
            "status": upload.status,
            "total_rows": upload.total_rows,
            "matched_count": upload.matched_count,
            "unmatched_count": upload.unmatched_count,
            "unmatched_rows": upload.unmatched_rows,
            "snapshot_count": upload.snapshots.count(),
        }

        if upload.status == "failed":
            response_data["error"] = upload.error_message
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        return Response(response_data, status=status.HTTP_201_CREATED)


class MPDOverviewView(APIView):
    """
    GET: Latest MPD snapshot data per active missionary (admin only).

    Returns per-user financial summary: current_mpd_cap,
    latest_roll_forward_balance, months_remaining_rf.

    Uses a single query with Subquery to fetch the latest snapshot per user
    instead of N+1 per-user queries.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.dashboard.services import get_mpd_computed
        from apps.users.models import User

        # Get all active missionaries
        users = User.objects.filter(
            role='missionary', is_active=True
        ).order_by('last_name', 'first_name')

        # Prefetch latest snapshot per user for monthly_average
        from apps.imports.models import MPDSnapshot as MPDSnapshotModel
        snapshot_map = {}
        for snap in MPDSnapshotModel.objects.filter(
            user__in=users
        ).select_related('upload').order_by('user_id', '-upload__created_at'):
            if snap.user_id not in snapshot_map:
                snapshot_map[snap.user_id] = snap

        missionaries = []
        for user in users:
            computed = get_mpd_computed(user)
            snapshot = snapshot_map.get(user.id)
            if computed.get("has_data") or (snapshot and snapshot.monthly_average is not None):
                entry = {
                    "user_id": str(user.id),
                    "user_name": user.full_name,
                    "monthly_average": str(snapshot.monthly_average) if snapshot and snapshot.monthly_average else None,
                }
                entry.update({k: v for k, v in computed.items() if k != "has_data"})
                missionaries.append(entry)

        return Response({"missionaries": missionaries})


class MPDMyDataView(APIView):
    """
    GET: Current user's computed MPD financial data (any authenticated user).

    Computes Monthly Average, Roll Forward Balance, and Months Remaining
    from actual Gift data in the current fiscal year.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.dashboard.services import get_mpd_computed

        data = get_mpd_computed(request.user)

        # Include snapshot's monthly_average if available
        snapshot = MPDSnapshot.objects.filter(user=request.user).order_by("-upload__created_at").first()
        data['monthly_average'] = str(snapshot.monthly_average) if snapshot and snapshot.monthly_average else None

        return Response(data)


class MPDUploadHistoryView(APIView):
    """
    GET: Last 10 completed MPD uploads (admin only).

    Returns upload history for the admin dashboard.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        uploads = MPDUpload.objects.filter(status="completed").order_by("-created_at")[:10]

        data = [
            {
                "id": str(upload.id),
                "filename": upload.filename,
                "created_at": upload.created_at.isoformat(),
                "total_rows": upload.total_rows,
                "matched_count": upload.matched_count,
                "unmatched_count": upload.unmatched_count,
            }
            for upload in uploads
        ]

        return Response({"uploads": data})


class ImportBatchListView(APIView):
    """GET: List recent ImportBatch records for import history display.

    Note: Uses hand-built dict instead of serializer class -- Phase 32
    decision for simplicity (only 12 fields, no nested relations).
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.imports.models import ImportBatch

        qs = ImportBatch.objects.select_related("uploaded_by").order_by("-created_at")

        import_type = request.query_params.get("import_type")
        if import_type:
            qs = qs.filter(import_type=import_type)

        # Cap at 50 recent records (no pagination needed)
        batches = qs[:50]

        data = [
            {
                "id": str(b.id),
                "import_type": b.import_type,
                "import_type_display": b.get_import_type_display(),
                "status": b.status,
                "filename": b.filename,
                "total_rows": b.total_rows,
                "created_count": b.created_count,
                "updated_count": b.updated_count,
                "skipped_count": b.skipped_count,
                "error_count": b.error_count,
                "created_at": b.created_at.isoformat(),
                "uploaded_by": b.uploaded_by.full_name,
            }
            for b in batches
        ]

        return Response(data)


class RESolicitorImportView(APIView):
    """
    POST: Import RE Solicitor CSV file (admin only).

    Accepts CSV file upload. Parses solicitor names, deduplicates via SHA256
    hash and external ID/normalized name, auto-links to User accounts.
    Returns ImportBatch result as JSON.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        force = str(request.data.get("force", "false")).lower() == "true"

        batch = import_re_solicitors(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            force=force,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


class GenericContactImportView(APIView):
    """
    POST: Import contacts from a generic CSV file.

    Accepts CSV file upload with configurable contact matching strategy
    (name, email, or external_id). Staff users and above can access.
    Returns ImportBatch result in the same shape as RE import views.
    """

    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match_by = request.data.get("match_by", "email")
        if match_by not in VALID_MATCH_BY:
            return Response(
                {"detail": f'Invalid match_by value. Must be one of: {", ".join(VALID_MATCH_BY)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        batch = import_generic_contacts(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            owner=request.user,
            match_by=match_by,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


class GenericDonationImportView(APIView):
    """
    POST: Import donations from a generic CSV file.

    Accepts CSV file upload with configurable contact matching strategy
    (name, email, or external_id). Creates Gift records linked to
    existing contacts. Staff users and above can access.
    Returns ImportBatch result in the same shape as RE import views.
    """

    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match_by = request.data.get("match_by", "email")
        if match_by not in VALID_MATCH_BY:
            return Response(
                {"detail": f'Invalid match_by value. Must be one of: {", ".join(VALID_MATCH_BY)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        batch = import_generic_donations(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            owner=request.user,
            match_by=match_by,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


class REConstituentImportView(APIView):
    """
    POST: Import RE Constituent CSV file (admin only).

    Accepts CSV file upload. Matches contacts by external_constituent_id,
    email, or phone (three-tier hierarchy). Merge-only updates fill blank
    fields without overwriting existing values. Returns ImportBatch result.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        force = str(request.data.get("force", "false")).lower() == "true"

        batch = import_re_constituents(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            owner=request.user,
            force=force,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


class REGiftImportView(APIView):
    """
    POST: Import RE Gift CSV file (admin only).

    Accepts CSV file upload. Groups rows by Gift ID, creates Gift + GiftCredit
    records with solicitor credit splitting, and auto-creates PrayerIntention
    records from prayer description column. Returns ImportBatch result as JSON.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        force = str(request.data.get("force", "false")).lower() == "true"

        batch = import_re_gifts(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            owner=request.user,
            force=force,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


class RERecurringGiftImportView(APIView):
    """
    POST: Import RE Recurring Gift CSV file (admin only).

    Accepts CSV file upload. Groups rows by Recurring Gift ID, maps frequency
    and status strings to Django choices, creates RecurringGift +
    RecurringGiftCredit records. Returns ImportBatch result as JSON.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        force = str(request.data.get("force", "false")).lower() == "true"

        batch = import_re_recurring_gifts(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
            owner=request.user,
            force=force,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


# ---------------------------------------------------------------------------
# SPO import views
# ---------------------------------------------------------------------------


class SPOMissionaryImportView(APIView):
    """
    POST: Reconcile SPO missionary accounts from Solicitors CSV (admin only).

    Step 1 of the SPO import pipeline. Accepts CSV file upload.
    Matches solicitor names to existing User accounts via three-level lookup,
    auto-creates missionaries for unmatched names.
    Returns ImportBatch result as JSON.

    Note: force=True not supported via API — use the CLI command for force re-imports.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        batch = reconcile_missionaries(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


class SPOGiftImportView(APIView):
    """
    POST: Import SPO gifts and attribute to missionaries (admin only).

    Step 2 of the SPO import pipeline. Accepts CSV file upload.
    Groups rows by Gift ID, creates Gift + GiftCredit records with missionary
    attribution. Returns ImportBatch result as JSON.

    Note: force=True not supported via API — use the CLI command for force re-imports.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        batch = import_spo_gifts(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )


class SPOPrayerImportView(APIView):
    """
    POST: Extract prayer intentions from SPO gifts CSV (admin only).

    Step 3 of the SPO import pipeline (prayer-only rerun pass).
    Accepts the same CSV format as the gifts endpoint but only extracts
    prayer intentions — no Gift or GiftCredit records created.
    Returns ImportBatch result as JSON.

    Note: force=True not supported via API — use the CLI command for force re-imports.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["file"]
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_bytes = file.read()

        batch = import_spo_prayers(
            file_bytes=file_bytes,
            filename=file.name,
            uploaded_by=request.user,
        )

        return Response(
            {
                "batch_id": str(batch.id),
                "status": batch.status,
                "is_duplicate": batch.status == ImportBatchStatus.DUPLICATE,
                "created_count": batch.created_count,
                "updated_count": batch.updated_count,
                "skipped_count": batch.skipped_count,
                "error_count": batch.error_count,
                "total_rows": batch.total_rows,
                "summary": batch.summary,
            }
        )
