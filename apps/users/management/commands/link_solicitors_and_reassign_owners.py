"""Management command: link unlinked solicitors to User accounts and reassign contact owners.

Steps:
  1. For each Solicitor with user=None, create a missionary User account
     (email derived from normalized name, unusable password).
  2. Link the Solicitor to that User.
  3. For each contact currently owned by a non-missionary user, find the
     solicitor credited with the highest total gift amount for that contact,
     then set contact.owner to that solicitor's user.

Use --dry-run to preview without writing.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.gifts.models import GiftCredit, Solicitor
from apps.users.models import User, UserRole


def _solicitor_to_email(normalized_name: str) -> str:
    """Convert 'last, first' to 'first.last@spo.org'."""
    parts = [p.strip() for p in normalized_name.split(',', 1)]
    if len(parts) == 2:
        last, first = parts
        return f"{first.lower()}.{last.lower()}@spo.org"
    return f"{normalized_name.replace(' ', '.').lower()}@spo.org"


def _solicitor_to_names(normalized_name: str) -> tuple[str, str]:
    """Convert 'last, first' to (first, last)."""
    parts = [p.strip() for p in normalized_name.split(',', 1)]
    if len(parts) == 2:
        return parts[1], parts[0]
    return normalized_name, ''


class Command(BaseCommand):
    help = (
        'Create User accounts for unlinked solicitors, link them, '
        'then reassign contact owners based on gift credits.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.\n'))

        # ── Step 1 & 2: Create users and link solicitors ──────────────────────

        unlinked = Solicitor.objects.filter(user__isnull=True).select_related()
        self.stdout.write(f'Found {unlinked.count()} unlinked solicitor(s).\n')

        solicitors_linked = 0
        users_created = 0

        for solicitor in unlinked:
            email = _solicitor_to_email(solicitor.normalized_name)
            first_name, last_name = _solicitor_to_names(solicitor.normalized_name)

            existing = User.objects.filter(email=email).first()
            if existing:
                user = existing
                self.stdout.write(
                    f'  Reusing existing user {email} for solicitor "{solicitor.normalized_name}"'
                )
            else:
                self.stdout.write(
                    f'  Creating user {email} for solicitor "{solicitor.normalized_name}"'
                )
                if not dry_run:
                    user = User.objects.create(
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        role=UserRole.MISSIONARY,
                        is_active=True,
                    )
                    user.set_unusable_password()
                    user.save()
                users_created += 1

            if not dry_run:
                solicitor.user = user
                solicitor.save()
            solicitors_linked += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Step 1+2: {users_created} user(s) created, '
                f'{solicitors_linked} solicitor(s) linked.\n'
            )
        )

        # ── Step 3: Reassign contact owners ───────────────────────────────────
        #
        # For each contact NOT already owned by a missionary, find the solicitor
        # with the highest total credit amount across all that contact's gifts.
        # Set contact.owner = that solicitor's user.

        # Collect all contacts owned by non-missionaries
        non_missionary_owners = User.objects.exclude(role=UserRole.MISSIONARY).values_list('id', flat=True)

        from apps.contacts.models import Contact  # avoid circular at module level
        contacts_to_fix = Contact.objects.filter(owner_id__in=non_missionary_owners)
        self.stdout.write(f'Found {contacts_to_fix.count()} contact(s) owned by non-missionaries.\n')

        reassigned = 0
        skipped_no_credits = 0

        for contact in contacts_to_fix:
            # Find solicitor with highest total credit amount for this contact's gifts
            top = (
                GiftCredit.objects
                .filter(gift__donor_contact=contact, solicitor__user__isnull=False)
                .values('solicitor__user')
                .annotate(total=Sum('amount_cents'))
                .order_by('-total')
                .first()
            )

            if not top:
                skipped_no_credits += 1
                self.stdout.write(
                    f'  SKIP {contact.id} ({contact.first_name} {contact.last_name})'
                    ' — no credited solicitor with a linked user'
                )
                continue

            new_owner_id = top['solicitor__user']
            new_owner = User.objects.get(pk=new_owner_id)
            self.stdout.write(
                f'  REASSIGN {contact.first_name} {contact.last_name or contact.organization_name}'
                f' → {new_owner.email}'
            )

            if not dry_run:
                contact.owner = new_owner
                contact.save(update_fields=['owner_id'])
            reassigned += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Step 3: {reassigned} contact(s) reassigned, '
                f'{skipped_no_credits} skipped (no linked solicitor).\n'
            )
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run complete — no changes written.'))
        else:
            self.stdout.write(self.style.SUCCESS('Done.'))
