from django.core.management.base import BaseCommand
from apps.users.models import User, UserRole
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create test missionary accounts for Render DB'

    def handle(self, *args, **options):
        PASSWORD = 'Test1234'

        missionaries = [
            ('Joe', 'Man', Decimal('2200')),
            ('Frank', 'Guy', Decimal('4300')),
            ('Rachel', 'Gal', Decimal('1100')),
            ('Jimmy', 'John', Decimal('2700')),
            ('Ronald', 'McDonald', Decimal('2200')),
            ('Rose', 'Red', Decimal('550')),
            ('Mary', 'Grace', Decimal('2200')),
            ('Simon', 'Peter', Decimal('2200')),
            ('John', 'Paul', Decimal('1850')),
            ('Sarah', 'Female', Decimal('2200')),
            ('Wendy', 'Burger', Decimal('2200')),
        ]

        new_count = 0
        for first, last, goal in missionaries:
            email = f'{first.lower()}.{last.lower()}@spo.org'
            user, was_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': UserRole.MISSIONARY,
                    'monthly_goal': goal,
                    'is_active': True,
                }
            )
            user.set_password(PASSWORD)
            user.save()
            status = 'Created' if was_created else 'Updated'
            self.stdout.write(f'  {status}: {first} {last} ({email})')
            if was_created:
                new_count += 1

        # Alex Becker — admin account
        alex, alex_created = User.objects.get_or_create(
            email='alex.becker@spo.org',
            defaults={
                'first_name': 'Alex',
                'last_name': 'Becker',
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_active': True,
            }
        )
        alex.set_password(PASSWORD)
        alex.save()
        self.stdout.write(
            f'  {"Created" if alex_created else "Updated"}: Alex Becker (alex.becker@spo.org) [admin]'
        )
        if alex_created:
            new_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {new_count} new account(s) created, password: {PASSWORD}'
        ))
