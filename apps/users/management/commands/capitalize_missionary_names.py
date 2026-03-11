"""Capitalize first and last name of all missionary users."""
from django.core.management.base import BaseCommand
from apps.users.models import User, UserRole


class Command(BaseCommand):
    help = 'Capitalize first and last name of all missionary users.'

    def handle(self, *args, **options):
        updated = 0
        for u in User.objects.filter(role=UserRole.MISSIONARY):
            nf = u.first_name.capitalize()
            nl = u.last_name.capitalize()
            if u.first_name != nf or u.last_name != nl:
                u.first_name = nf
                u.last_name = nl
                u.save(update_fields=['first_name', 'last_name'])
                updated += 1
                self.stdout.write(f'  {u.email}: {nf} {nl}')
        self.stdout.write(self.style.SUCCESS(f'Done. {updated} user(s) updated.'))
