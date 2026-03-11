import random
from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    help = 'Set a random monthly_goal (2500-5000, rounded to nearest 100) for missionary accounts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing goals (default: only set if currently null or zero)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving',
        )

    def handle(self, *args, **options):
        overwrite = options['overwrite']
        dry_run = options['dry_run']

        qs = User.objects.filter(role='missionary', is_active=True)
        if not overwrite:
            qs = qs.filter(monthly_goal__isnull=True) | User.objects.filter(
                role='missionary', is_active=True, monthly_goal=0
            )
            # Re-evaluate as a list to avoid ORM union issues
            ids_no_goal = list(
                User.objects.filter(role='missionary', is_active=True)
                .exclude(monthly_goal__gt=0)
                .values_list('id', flat=True)
            )
            qs = User.objects.filter(id__in=ids_no_goal)

        missionaries = list(qs.order_by('email'))

        if not missionaries:
            self.stdout.write('No missionary accounts to update (all already have goals set).')
            return

        self.stdout.write(
            f'{"[DRY RUN] " if dry_run else ""}Setting monthly goals for {len(missionaries)} missionary account(s):\n'
        )

        for user in missionaries:
            # Random multiple of 100 between 2500 and 5000 inclusive
            goal = random.randint(25, 50) * 100
            self.stdout.write(f'  {user.email}: ${goal:,}')
            if not dry_run:
                user.monthly_goal = goal
                user.save(update_fields=['monthly_goal'])

        if dry_run:
            self.stdout.write('\nDry run complete — no changes saved.')
        else:
            self.stdout.write(f'\nDone. Updated {len(missionaries)} account(s).')
