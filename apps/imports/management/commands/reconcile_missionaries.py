"""
Management command for Step 1 of the SPO import pipeline.

Reconciles SPO missionary accounts from a Solicitors CSV file.

Usage:
    python manage.py reconcile_missionaries <file> --owner admin@example.com [--force]
"""
from django.core.management.base import BaseCommand, CommandError

from apps.imports.models import ImportBatchStatus
from apps.imports.spo_services import reconcile_missionaries
from apps.users.models import User

# Maximum upload size: 10 MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


class Command(BaseCommand):
    help = "Step 1: Reconcile SPO missionary accounts from Solicitors CSV"

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
        batch = reconcile_missionaries(
            file_bytes=file_bytes,
            filename=filename,
            uploaded_by=owner_user,
            force=options["force"],
        )

        self._print_summary(batch, self.stdout)

    def _print_summary(self, batch, stdout):
        """Print formatted audit table for the missionary reconciliation result."""
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

        # Success: print aggregate section
        summary = batch.summary
        stdout.write(self.style.SUCCESS("\n=== SPO Missionary Reconciliation Complete ===\n"))
        stdout.write("Aggregate:")
        stdout.write(f'  Missionaries in CSV:    {summary.get("missionaries_expected", 0)}')
        stdout.write(f'  Matched (exact):         {summary.get("matched_exact", 0)}')
        stdout.write(f'  Matched (normalized):    {summary.get("matched_normalized", 0)}')
        stdout.write(f'  Matched (alias):         {summary.get("matched_alias", 0)}')
        stdout.write(f'  Created (new):           {summary.get("created", 0)}')
        stdout.write(f'  Unresolved:              {summary.get("unresolved", 0)}')

        # Per-missionary table
        per_missionary = summary.get("per_missionary", [])
        if per_missionary:
            stdout.write("\nPer-Missionary:")
            stdout.write(f'  {"Name":<22} {"Match Type":<12} {"Gifts":>6}   Status')
            stdout.write("  " + "\u2500" * 50)
            for entry in per_missionary:
                name = entry.get("name", "")
                match_type = entry.get("match_type", "")
                gifts_imported = entry.get("gifts_imported", 0)

                if gifts_imported == 0:
                    status_str = self.style.WARNING(
                        "ZERO DONATIONS \u2014 verify import ran correctly"
                    )
                else:
                    status_str = match_type

                stdout.write(f"  {name:<22} {match_type:<12} {gifts_imported:>6}   {status_str}")

        # Unresolved names
        unresolved_names = summary.get("unresolved_names", [])
        if unresolved_names:
            stdout.write(f"\nUnresolved names ({len(unresolved_names)}):")
            for name in unresolved_names:
                stdout.write(f"  - {name}")
            stdout.write(
                self.style.WARNING(
                    "\nRerun with --force after adding aliases to MissionaryAlias table."
                )
            )

        stdout.write(f"\nUnresolved names saved to ImportBatch #{batch.id} summary.")
