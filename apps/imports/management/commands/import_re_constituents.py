"""
Management command for importing RE Constituent CSV files.

Usage:
    python manage.py import_re_constituents <file> --owner admin@example.com
"""
import os

from django.core.management.base import BaseCommand, CommandError

from apps.imports.models import ImportBatchStatus
from apps.imports.re_services import import_re_constituents
from apps.users.models import User

# Maximum upload size: 10 MB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


class Command(BaseCommand):
    help = 'Import RE Constituent CSV file'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to CSV file')
        parser.add_argument(
            '--owner',
            type=str,
            required=True,
            help='Email of the user who will own new contacts AND who is recorded as uploaded_by',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        owner_email = options['owner']

        # Look up owner user by email
        try:
            owner_user = User.objects.get(email=owner_email)
        except User.DoesNotExist:
            raise CommandError(f'User not found: {owner_email}')

        if not owner_user.is_active:
            raise CommandError(f'User is not active: {owner_email}')

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

        filename = os.path.basename(file_path)
        self.stdout.write(f'Processing {filename}...')

        # Call shared service
        batch = import_re_constituents(
            file_bytes=file_bytes,
            filename=filename,
            uploaded_by=owner_user,
            owner=owner_user,
        )

        # Check for duplicate
        if batch.status == ImportBatchStatus.DUPLICATE:
            self.stdout.write(self.style.WARNING(
                f'File already imported (batch {batch.id}). Skipping.'
            ))
            return

        # Check for failure
        if batch.status == ImportBatchStatus.FAILED:
            file_error = batch.summary.get('file_error', 'Unknown error')
            self.stdout.write(self.style.ERROR(
                f'Import failed: {file_error}'
            ))
            return

        # Print success summary
        self.stdout.write(self.style.SUCCESS(f'Import complete: {batch.filename}'))
        self.stdout.write(f'  Created: {batch.created_count}')
        self.stdout.write(f'  Updated: {batch.updated_count}')
        self.stdout.write(f'  Skipped: {batch.skipped_count}')
        self.stdout.write(f'  Errors: {batch.error_count}')

        # Print warnings count
        warnings = batch.summary.get('warnings', [])
        if warnings:
            self.stdout.write(f'  Warnings: {len(warnings)}')

        # Print errors
        errors = batch.summary.get('errors', [])
        if errors:
            self.stdout.write(self.style.WARNING(f'\n  Errors ({len(errors)}):'))
            for err in errors[:10]:
                self.stdout.write(f'    Row {err["row"]}: {err["error"]}')
            if len(errors) > 10:
                self.stdout.write(f'    ... and {len(errors) - 10} more')
