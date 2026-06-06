"""Set realistic monthly_support_goal_cents for test missionaries.

One-shot command to update missionary goals so dashboard percentages
show a natural distribution (67%–104% from recurring alone).
"""

from django.core.management.base import BaseCommand

from apps.users.models import User

# (email, goal_cents) — goal in cents, derived from actual test_data recurring totals
MISSIONARY_GOALS = [
    ("nicole.robinson@spo.org", 420000),
    ("jessica.davis@spo.org", 380000),
    ("kevin.young@spo.org", 390000),
    ("emily.brown@spo.org", 340000),
    ("amanda.anderson@spo.org", 320000),
    ("lauren.hall@spo.org", 340000),
    ("joshua.garcia@spo.org", 350000),
    ("andrew.clark@spo.org", 340000),
    ("john.smith@spo.org", 490000),
    ("daniel.miller@spo.org", 410000),
    ("jennifer.martinez@spo.org", 430000),
    ("stephanie.lewis@spo.org", 410000),
    ("david.jones@spo.org", 450000),
    ("sarah.johnson@spo.org", 480000),
    ("ashley.wilson@spo.org", 470000),
    ("christopher.thomas@spo.org", 430000),
    ("matthew.taylor@spo.org", 450000),
    ("ryan.walker@spo.org", 440000),
    ("michael.williams@spo.org", 450000),
    ("michelle.king@spo.org", 280000),
]


class Command(BaseCommand):
    help = "Set realistic monthly support goals for test missionary accounts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved.\n"))

        updated = 0
        skipped = 0

        for email, goal_cents in MISSIONARY_GOALS:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(f"  SKIP {email} — user not found")
                skipped += 1
                continue

            old_goal = user.monthly_support_goal_cents
            goal_dollars = goal_cents / 100
            old_dollars = old_goal / 100 if old_goal else 0

            self.stdout.write(
                f"  {user.full_name} ({email}): "
                f"${old_dollars:,.0f}/mo → ${goal_dollars:,.0f}/mo"
            )

            if not dry_run:
                user.monthly_support_goal_cents = goal_cents
                user.save(update_fields=["monthly_support_goal_cents"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n{updated} goal(s) updated, {skipped} skipped."))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete — no changes written."))
