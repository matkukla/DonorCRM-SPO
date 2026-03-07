"""
Management command for Step 2 of the SPO import pipeline.

Imports SPO gifts and attributes them to missionaries via GiftCredit.

Usage:
    python manage.py import_spo_gifts <file> --owner admin@example.com [--force]
"""
from django.core.management.base import BaseCommand, CommandError

from apps.imports.models import ImportBatchStatus
from apps.imports.spo_services import import_spo_gifts
from apps.users.models import User

# Maximum upload size: 10 MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


class Command(BaseCommand):
    help = 'Step 2: Import SPO gifts and attribute to missionaries'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to CSV file')
        parser.add_argument(
            '--owner',
            type=str,
            required=True,
            help='Email of the user who runs the import (used as uploaded_by)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Bypass SHA256 dedup (use after adding aliases to MissionaryAlias table)',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        owner_email = options['owner']

        # Look up owner user by email
        try:
            owner_user = User.objects.get(email=owner_email)
        except User.DoesNotExist:
            raise CommandError(f'User not found: {owner_email}')

        # Read file bytes
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')

        # Check file size
        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise CommandError(
                f'File too large ({len(file_bytes):,} bytes). Maximum is 10 MB.'
            )

        # Extract filename from path
        filename = file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path

        self.stdout.write(f'Processing {filename}...')

        # Call shared service
        batch = import_spo_gifts(
            file_bytes=file_bytes,
            filename=filename,
            uploaded_by=owner_user,
            force=options['force'],
        )

        self._print_summary(batch, self.stdout)

    def _print_summary(self, batch, stdout):
        """Print formatted audit table for the SPO gift import result."""
        # Handle duplicate
        if batch.status == ImportBatchStatus.DUPLICATE:
            stdout.write(self.style.WARNING(
                f'File already imported (batch {batch.id}). Use --force to re-import.'
            ))
            return

        # Handle failure
        if batch.status == ImportBatchStatus.FAILED:
            errors = batch.summary.get('errors', []) or batch.summary.get('error_details', [])
            stdout.write(self.style.ERROR(f'Import failed: {batch.filename}'))
            for err in errors[:10]:
                stdout.write(self.style.ERROR(f'  Row {err["row"]}: {err["error"]}'))
            return

        # Success: aggregate counts
        summary = batch.summary
        stdout.write(self.style.SUCCESS('\n=== SPO Gift Import Complete ===\n'))
        stdout.write('Aggregate:')
        stdout.write(f'  Gifts created:          {summary.get("created", batch.created_count)}')
        stdout.write(f'  Skipped:                {summary.get("skipped", batch.skipped_count)}')
        stdout.write(f'  Errors:                 {summary.get("errors", batch.error_count)}')

        # Contact not found
        contact_not_found = summary.get('contact_not_found', [])
        if contact_not_found:
            stdout.write(self.style.WARNING(
                f'\n  Contacts not found ({len(contact_not_found)} constituent IDs):'
            ))
            for cid in contact_not_found[:20]:
                stdout.write(f'    - {cid}')
            if len(contact_not_found) > 20:
                stdout.write(f'    ... and {len(contact_not_found) - 20} more')

        # Unmatched/unresolved solicitor names
        unmatched_unresolved = summary.get('unmatched_unresolved', [])
        if unmatched_unresolved:
            stdout.write(self.style.WARNING(
                f'\n  Unresolved solicitor names ({len(unmatched_unresolved)}):'
            ))
            seen = set()
            unique = [n for n in unmatched_unresolved if not (n in seen or seen.add(n))]
            for name in unique[:20]:
                stdout.write(f'    - {name}')
            if len(unique) > 20:
                stdout.write(f'    ... and {len(unique) - 20} more')

        # Per-missionary gift table (abbreviated)
        per_missionary = summary.get('per_missionary', [])
        if per_missionary:
            # Aggregate per missionary
            agg: dict = {}
            for entry in per_missionary:
                missionary = entry.get('missionary', 'Unknown')
                agg.setdefault(missionary, {'count': 0, 'total_cents': 0})
                agg[missionary]['count'] += 1
                agg[missionary]['total_cents'] += entry.get('amount_cents', 0)

            stdout.write('\nPer-Missionary Gift Summary:')
            stdout.write(f'  {"Missionary":<30} {"Gifts":>6}   Total')
            stdout.write('  ' + '\u2500' * 50)
            for name, data in sorted(agg.items()):
                total_dollars = data['total_cents'] / 100
                stdout.write(f'  {name:<30} {data["count"]:>6}   ${total_dollars:,.2f}')
