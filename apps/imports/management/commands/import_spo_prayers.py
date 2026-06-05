"""
Management command for Step 3 of the SPO import pipeline.

Extracts prayer intentions from SPO gifts CSV (prayer-only rerun pass).

Usage:
    python manage.py import_spo_prayers <file> --owner admin@example.com [--force]
"""
from django.core.management.base import BaseCommand, CommandError

from apps.imports.models import ImportBatchStatus
from apps.imports.spo_services import import_spo_prayers
from apps.users.models import User

# Maximum upload size: 10 MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


class Command(BaseCommand):
    help = "Step 3: Extract prayer intentions from SPO gifts CSV (prayer-only rerun)"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to CSV file")
        parser.add_argument(
            "--owner",
            type=str,
            required=True,
            help="Email of the user who runs the import (used as uploaded_by)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Bypass SHA256 dedup (use after adding aliases to MissionaryAlias table)",
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
        batch = import_spo_prayers(
            file_bytes=file_bytes,
            filename=filename,
            uploaded_by=owner_user,
            force=options["force"],
        )

        self._print_summary(batch, self.stdout)

    def _print_summary(self, batch, stdout):
        """Print formatted output for the prayer extraction result."""
        # Handle duplicate
        if batch.status == ImportBatchStatus.DUPLICATE:
            stdout.write(
                self.style.WARNING(
                    f"File already imported (batch {batch.id}). Use --force to re-import."
                )
            )
            return

        # Handle failure
        if batch.status == ImportBatchStatus.FAILED:
            errors = batch.summary.get("errors", [])
            stdout.write(self.style.ERROR(f"Import failed: {batch.filename}"))
            for err in errors[:10]:
                stdout.write(self.style.ERROR(f'  Row {err["row"]}: {err["error"]}'))
            return

        # Success: simple aggregate output (prayer-only pass)
        summary = batch.summary
        prayers_created = summary.get("prayers_created", batch.created_count)
        skipped = summary.get("skipped", batch.skipped_count)

        stdout.write(self.style.SUCCESS("\n=== SPO Prayer Extraction Complete ===\n"))
        stdout.write("Aggregate:")
        stdout.write(f"  Prayer intentions created: {prayers_created}")
        stdout.write(f"  Rows skipped:              {skipped}")
        stdout.write(f"  (Rows without prayer description or unresolvable contacts are skipped)")
