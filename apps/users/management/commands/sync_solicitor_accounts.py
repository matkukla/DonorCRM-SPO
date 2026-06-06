"""
Management command to ensure all solicitor accounts from test_solicitors.csv
exist with @spo.org emails and a consistent password.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

SOLICITORS = [
    ("Peter", "Anderson"),
    ("Ben", "Wagner"),
    ("Daniel", "Robinson"),
    ("Rebecca", "Thompson"),
    ("Mary", "Anderson"),
    ("Esther", "Wagner"),
    ("Joy", "Campbell"),
    ("Stephen", "Wallace"),
    ("Sarah", "Huntley"),
    ("Michael", "Peterson"),
    ("Rebecca", "Henderson"),
    ("Ruth", "Huntley"),
    ("Joy", "Peterson"),
    ("Paul", "Simmons"),
    ("Paul", "Crawford"),
    ("Faith", "Robinson"),
    ("James", "Marshall"),
    ("Daniel", "Huntley"),
    ("John", "Mitchell"),
    ("Paul", "Wallace"),
    ("Matthew", "Harrison"),
    ("David", "Peterson"),
    ("John", "Freeman"),
    ("Rachel", "Campbell"),
    ("Andrew", "Anderson"),
]

SOLICITOR_PASSWORD = os.environ.get("DEMO_USER_PASSWORD", "changeme")


def solicitor_email(first, last):
    return f"{first.lower()}.{last.lower()}@spo.org"


class Command(BaseCommand):
    help = "Ensure all solicitor accounts exist with consistent @spo.org emails and password"

    def handle(self, *args, **options):
        # 1. Migrate any non-@spo.org email accounts to @spo.org (based on first/last name)
        non_spo = User.objects.exclude(email__endswith="@spo.org")
        if non_spo.exists():
            self.stdout.write("Migrating non-@spo.org accounts:")
            for user in non_spo:
                if user.first_name and user.last_name:
                    new_email = solicitor_email(user.first_name, user.last_name)
                else:
                    local = user.email.split("@")[0]
                    new_email = f"{local}@spo.org"
                old_email = user.email
                # Avoid collision if the target email already exists
                if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                    self.stdout.write(f"  SKIP {old_email} -> {new_email} (collision)")
                    continue
                user.email = new_email
                user.set_password(SOLICITOR_PASSWORD)
                user.save()
                self.stdout.write(f"  {old_email} -> {new_email}")

        # 2. Rename admin.user@spo.org -> admin@spo.org if it exists
        try:
            u = User.objects.get(email="admin.user@spo.org")
            if not User.objects.filter(email="admin@spo.org").exclude(pk=u.pk).exists():
                u.email = "admin@spo.org"
                u.set_password(SOLICITOR_PASSWORD)
                u.save()
                self.stdout.write("Renamed admin.user@spo.org -> admin@spo.org")
        except User.DoesNotExist:
            pass

        # 3. Ensure each solicitor has a correct account with the right password
        ACCOUNTS = SOLICITORS + [("Jonathan", "Ryan")]
        self.stdout.write(f"\nEnsuring {len(ACCOUNTS)} account(s):")
        for first, last in ACCOUNTS:
            email = solicitor_email(first, last)
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "is_active": True,
                },
            )
            if not created:
                user.first_name = first
                user.last_name = last
            user.set_password(SOLICITOR_PASSWORD)
            user.save()
            action = "created" if created else "updated"
            self.stdout.write(f"  {email} ({action})")

        # 4. Ensure admin@spo.org has the correct password
        try:
            admin = User.objects.get(email="admin@spo.org")
            admin.set_password(SOLICITOR_PASSWORD)
            admin.save()
            self.stdout.write("  admin@spo.org (updated)")
        except User.DoesNotExist:
            pass

        self.stdout.write(
            self.style.SUCCESS("\nDone. Password set from DEMO_USER_PASSWORD env var.")
        )
