from django.core.management.base import BaseCommand

from apps.core.demo_accounts import assert_not_production, resolve_demo_password
from apps.users.models import User, UserRole


class Command(BaseCommand):
    help = "Create test missionary accounts for Render DB (local/dev only)"

    def handle(self, *args, **options):
        assert_not_production()
        PASSWORD = resolve_demo_password()

        # Tuples: (first, last, goal_cents)  — values are dollar amounts × 100
        missionaries = [
            ("Joe", "Man", 220000),
            ("Frank", "Guy", 430000),
            ("Rachel", "Gal", 110000),
            ("Jimmy", "John", 270000),
            ("Ronald", "McDonald", 220000),
            ("Rose", "Red", 55000),
            ("Mary", "Grace", 220000),
            ("Simon", "Peter", 220000),
            ("John", "Paul", 185000),
            ("Sarah", "Female", 220000),
            ("Wendy", "Burger", 220000),
        ]

        new_count = 0
        for first, last, goal_cents in missionaries:
            email = f"{first.lower()}.{last.lower()}@spo.org"
            user, was_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": UserRole.MISSIONARY,
                    "monthly_support_goal_cents": goal_cents,
                    "is_active": True,
                },
            )
            user.set_password(PASSWORD)
            user.save()
            status = "Created" if was_created else "Updated"
            self.stdout.write(f"  {status}: {first} {last} ({email})")
            if was_created:
                new_count += 1

        # Alex Becker — admin account
        alex, alex_created = User.objects.get_or_create(
            email="alex.becker@spo.org",
            defaults={
                "first_name": "Alex",
                "last_name": "Becker",
                "role": UserRole.ADMIN,
                "is_staff": True,
                "is_active": True,
            },
        )
        alex.set_password(PASSWORD)
        alex.save()
        action = "Created" if alex_created else "Updated"
        self.stdout.write(f"  {action}: Alex Becker (alex.becker@spo.org) [admin]")
        if alex_created:
            new_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. {new_count} new account(s) created, password: {PASSWORD}")
        )
