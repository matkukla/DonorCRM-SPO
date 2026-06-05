import random

from django.core.management.base import BaseCommand

from apps.users.models import User


class Command(BaseCommand):
    help = (
        "Set a random monthly_support_goal_cents (2500-5000, rounded to nearest 100) "
        "for missionary accounts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing goals (default: only set if currently null or zero)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving",
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite"]
        dry_run = options["dry_run"]

        qs = User.objects.filter(role="missionary", is_active=True)
        if not overwrite:
            # Re-evaluate as a list to avoid ORM union issues
            ids_no_goal = list(
                User.objects.filter(role="missionary", is_active=True)
                .exclude(monthly_support_goal_cents__gt=0)
                .values_list("id", flat=True)
            )
            qs = User.objects.filter(id__in=ids_no_goal)

        missionaries = list(qs.order_by("email"))

        if not missionaries:
            self.stdout.write("No missionary accounts to update (all already have goals set).")
            return

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            f"{prefix}Setting monthly goals for {len(missionaries)} missionary account(s):\n"
        )

        for user in missionaries:
            # Random multiple of 100 between 2500 and 5000 inclusive
            # goal in dollars (2500-5000, multiple of 100), convert to cents
            goal_dollars = random.randint(25, 50) * 100
            goal_cents = goal_dollars * 100
            self.stdout.write(f"  {user.email}: ${goal_dollars:,}")
            if not dry_run:
                user.monthly_support_goal_cents = goal_cents
                user.save(update_fields=["monthly_support_goal_cents"])

        if dry_run:
            self.stdout.write("\nDry run complete — no changes saved.")
        else:
            self.stdout.write(f"\nDone. Updated {len(missionaries)} account(s).")
