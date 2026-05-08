"""Hard-delete records past their retention window.

Drives the retention policy in ``docs/security/data-retention.md``. Runs
nightly via a Render cron job (TODO: wire) and logs every deletion class
with counts via ``apps.core.audit.audit_event``.

Defaults are conservative — pass ``--dry-run`` to count without deleting.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.audit import audit_event

# Per-class retention windows (days). Match docs/security/data-retention.md.
RETENTION_DAYS = {
    "soft_deleted_contacts": 365,
    "import_batches": 365,
    # DataAccessLog (Phase 6) — purge_expired_data also cleans this when
    # the model exists. The lookup below is conditional so this command
    # works pre-Phase-6.
    "data_access_log": 365,
}


class Command(BaseCommand):
    help = "Purge records past their retention window per data-retention.md."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count rows that would be deleted; do not delete.",
        )

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        now = timezone.now()

        self._purge_soft_deleted_contacts(now, dry_run)
        self._purge_import_batches(now, dry_run)
        self._purge_data_access_log(now, dry_run)

    def _purge_soft_deleted_contacts(self, now, dry_run: bool) -> None:
        """Hard-delete contacts merged ≥ retention days ago.

        Soft-deletion (``is_merged=True``) is operational; the merge log
        timestamp is the authoritative trigger for retention.
        """
        from apps.contacts.models import Contact, ContactMergeLog

        cutoff = now - timedelta(days=RETENTION_DAYS["soft_deleted_contacts"])
        old_merges = ContactMergeLog.objects.filter(created_at__lt=cutoff).values_list(
            "loser_id", flat=True
        )
        qs = Contact.objects.filter(pk__in=old_merges, is_merged=True)
        count = qs.count()
        if not dry_run and count:
            qs.delete()
        verb = "would delete" if dry_run else "deleted"
        self.stdout.write(f"soft_deleted_contacts: {verb}={count}")
        audit_event(
            "retention.purge.complete",
            target="contacts.Contact[is_merged]",
            count=count,
            dry_run=dry_run,
        )

    def _purge_import_batches(self, now, dry_run: bool) -> None:
        from apps.imports.models import ImportBatch

        cutoff = now - timedelta(days=RETENTION_DAYS["import_batches"])
        qs = ImportBatch.objects.filter(created_at__lt=cutoff)
        count = qs.count()
        if not dry_run and count:
            qs.delete()
        verb = "would delete" if dry_run else "deleted"
        self.stdout.write(f"import_batches: {verb}={count}")
        audit_event(
            "retention.purge.complete",
            target="imports.ImportBatch",
            count=count,
            dry_run=dry_run,
        )

    def _purge_data_access_log(self, now, dry_run: bool) -> None:
        """Purge DataAccessLog rows older than the retention window.

        No-op when the model isn't installed yet (pre-Phase-6).
        """
        try:
            from apps.core.models import DataAccessLog
        except ImportError:
            self.stdout.write("data_access_log: model not yet installed; skipping")
            return

        cutoff = now - timedelta(days=RETENTION_DAYS["data_access_log"])
        qs = DataAccessLog.objects.filter(timestamp__lt=cutoff)
        count = qs.count()
        if not dry_run and count:
            qs.delete()
        verb = "would delete" if dry_run else "deleted"
        self.stdout.write(f"data_access_log: {verb}={count}")
        audit_event(
            "retention.purge.complete",
            target="core.DataAccessLog",
            count=count,
            dry_run=dry_run,
        )
