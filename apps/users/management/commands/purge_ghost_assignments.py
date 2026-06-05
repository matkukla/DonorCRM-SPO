"""
Management command to remove ghost M2M assignment rows.

Ghost rows are M2M entries in users_user_supervisors or users_user_coaches
where the referenced user no longer holds the expected role (supervisor or coach).
These were created by migration 0006 which copied FK data without role validation.
"""
from django.core.management.base import BaseCommand

from apps.users.models import User


class Command(BaseCommand):
    help = "Purge ghost supervisor/coach M2M assignments where user role has changed"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be removed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        sup_removed = 0
        coach_removed = 0

        missionaries = User.objects.filter(role="missionary", is_active=True).prefetch_related(
            "supervisors", "coaches"
        )

        for missionary in missionaries:
            # Ghost supervisors: in M2M but no longer have role=supervisor
            ghost_sups = [
                u for u in missionary.supervisors.all() if u.role != "supervisor" or not u.is_active
            ]
            if ghost_sups:
                if not dry_run:
                    missionary.supervisors.remove(*ghost_sups)
                sup_removed += len(ghost_sups)
                for g in ghost_sups:
                    self.stdout.write(
                        f"{'[DRY RUN] ' if dry_run else ''}Removed ghost supervisor "
                        f"{g.email} (role={g.role}) from missionary {missionary.email}"
                    )

            # Ghost coaches: in M2M but no longer have role=coach
            ghost_coaches = [
                u for u in missionary.coaches.all() if u.role != "coach" or not u.is_active
            ]
            if ghost_coaches:
                if not dry_run:
                    missionary.coaches.remove(*ghost_coaches)
                coach_removed += len(ghost_coaches)
                for g in ghost_coaches:
                    self.stdout.write(
                        f"{'[DRY RUN] ' if dry_run else ''}Removed ghost coach "
                        f"{g.email} (role={g.role}) from missionary {missionary.email}"
                    )

        mode = "Would remove" if dry_run else "Removed"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} {sup_removed} ghost supervisor row(s) and "
                f"{coach_removed} ghost coach row(s)."
            )
        )
