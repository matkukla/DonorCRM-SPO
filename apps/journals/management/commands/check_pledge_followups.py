"""Create follow-up tasks for unfulfilled pledges past their 10-day mark.

A pledge is an active ``Decision``. Ten days after it is recorded, if the donor has
not given a qualifying gift (or started an active recurring gift), this creates one
follow-up Task for the owning missionary. Idempotent — safe to run repeatedly.

This is the production-deployable trigger (run as a Render cron); the same logic also
runs via the ``apps.journals.tasks.check_pledge_followups`` Celery beat task.

Pass ``--dry-run`` to count without creating anything.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.journals.pledge_followup import run_pledge_followup_sweep


class Command(BaseCommand):
    help = "Create follow-up tasks for unfulfilled pledges past their 10-day mark."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many follow-ups would be created without creating them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        count = run_pledge_followup_sweep(dry_run=dry_run)

        verb = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(f"{verb} {count} pledge follow-up task(s)."))
