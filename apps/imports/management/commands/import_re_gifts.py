"""
Management command for importing RE Gift CSV files.

Usage:
    python manage.py import_re_gifts <file> --owner admin@example.com [--force]
"""

from django.core.management.base import BaseCommand, CommandError

from apps.imports.models import ImportBatchStatus
from apps.imports.re_services import import_re_gifts
from apps.users.models import User

# Maximum upload size: 10 MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


class Command(BaseCommand):
    help = "Import RE Gift CSV file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to CSV file")
        parser.add_argument(
            "--owner",
            type=str,
            required=True,
            help="Email of the user who owns the imported gifts",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Bypass SHA256 dedup and update existing records",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        owner_email = options["owner"]

        # Look up owner user by email
        try:
            owner_user = User.objects.get(email=owner_email)
        except User.DoesNotExist:
            raise CommandError(f"User not found: {owner_email}")

        # Read file bytes
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")

        # Check file size
        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise CommandError(f"File too large ({len(file_bytes):,} bytes). Maximum is 10 MB.")

        # Extract filename from path
        filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path

        self.stdout.write(f"Processing {filename}...")

        # Call shared service
        batch = import_re_gifts(
            file_bytes=file_bytes,
            filename=filename,
            uploaded_by=owner_user,
            owner=owner_user,
            force=options["force"],
        )

        # Check for duplicate
        if batch.status == ImportBatchStatus.DUPLICATE:
            self.stdout.write(
                self.style.WARNING(
                    f"File already imported (batch {batch.id}). Use --force to re-import."
                )
            )
            return

        # Check for failure
        if batch.status == ImportBatchStatus.FAILED:
            errors = batch.summary.get("errors", [])
            self.stdout.write(self.style.ERROR(f"Import failed: {filename}"))
            for err in errors[:10]:
                self.stdout.write(self.style.ERROR(f'  Row {err["row"]}: {err["error"]}'))
            return

        # Print success summary
        self.stdout.write(self.style.SUCCESS(f"Import complete: {batch.filename}"))
        self.stdout.write(f"  Created: {batch.created_count}")
        self.stdout.write(f"  Skipped: {batch.skipped_count}")
        self.stdout.write(f"  Errors: {batch.error_count}")
        self.stdout.write(f'  Prayer intentions: {batch.summary.get("prayer_count", 0)}')

        # Print unmatched solicitors
        unmatched = batch.summary.get("unmatched_solicitors", [])
        if unmatched:
            self.stdout.write(
                self.style.WARNING(
                    f"\n  Unmatched solicitors ({len(unmatched)} " f"-- not in solicitor table):"
                )
            )
            for name in unmatched[:10]:
                self.stdout.write(f"    - {name}")
            if len(unmatched) > 10:
                self.stdout.write(f"    ... and {len(unmatched) - 10} more")

        # Print errors
        errors = batch.summary.get("errors", [])
        if errors:
            self.stdout.write(self.style.WARNING(f"\n  Errors ({len(errors)}):"))
            for err in errors[:10]:
                self.stdout.write(f'    Row {err["row"]}: {err["error"]}')
            if len(errors) > 10:
                self.stdout.write(f"    ... and {len(errors) - 10} more")
