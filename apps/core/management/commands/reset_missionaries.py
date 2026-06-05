"""
Management command to wipe all data, remove non-kept users,
and create fresh missionary accounts from test_solicitors.csv.
"""
import os

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Q

from apps.contacts.models import Contact
from apps.events.models import Event
from apps.gifts.models import Gift, GiftCredit, RecurringGift, RecurringGiftCredit, Solicitor
from apps.groups.models import Group
from apps.imports.models import (
    Fund,
    ImportBatch,
    ImportRowError,
    ImportRun,
    MissionaryAlias,
    MPDSnapshot,
    MPDUpload,
)
from apps.journals.models import (
    Decision,
    DecisionHistory,
    Journal,
    JournalContact,
    JournalStageEvent,
    NextStep,
)
from apps.prayers.models import PrayerIntention
from apps.tasks.models import Task
from apps.users.models import GoalJournalSelection, User, UserRole

PASSWORD = os.environ.get("DEMO_USER_PASSWORD", "changeme")
GOAL_CENTS = 220000

MISSIONARIES = [
    ("John", "Smith"),
    ("Sarah", "Johnson"),
    ("Michael", "Williams"),
    ("Emily", "Brown"),
    ("David", "Jones"),
    ("Jessica", "Davis"),
    ("Daniel", "Miller"),
    ("Ashley", "Wilson"),
    ("Matthew", "Taylor"),
    ("Amanda", "Anderson"),
    ("Christopher", "Thomas"),
    ("Jennifer", "Martinez"),
    ("Joshua", "Garcia"),
    ("Nicole", "Robinson"),
    ("Andrew", "Clark"),
    ("Stephanie", "Lewis"),
    ("Ryan", "Walker"),
    ("Lauren", "Hall"),
    ("Kevin", "Young"),
    ("Michelle", "King"),
]

# Users to keep: admins, superusers, and these specific people
KEEP_NAMES = [
    ("matthew", "kukla"),
    ("jonathan", "ryan"),
]


class Command(BaseCommand):
    help = "Wipe all data, remove non-kept users, and create fresh missionary accounts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually execute (dry-run by default)",
        )

    def handle(self, *args, **options):
        dry_run = not options["confirm"]

        # Build keep filter: superusers OR admins OR specific names
        keep_q = Q(is_superuser=True) | Q(role=UserRole.ADMIN)
        for first, last in KEEP_NAMES:
            keep_q |= Q(first_name__iexact=first, last_name__iexact=last)

        kept_users = User.objects.filter(keep_q)
        users_to_delete = User.objects.exclude(pk__in=kept_users.values_list("pk", flat=True))

        self.stdout.write("\n=== Users to KEEP ===")
        for u in kept_users:
            self.stdout.write(f"  {u.role:12} {u.full_name:25} {u.email}")

        self.stdout.write(f"\n=== Users to DELETE ({users_to_delete.count()}) ===")
        for u in users_to_delete:
            self.stdout.write(f"  {u.role:12} {u.full_name:25} {u.email}")

        self.stdout.write(f"\n=== New missionaries to CREATE ({len(MISSIONARIES)}) ===")
        for first, last in MISSIONARIES:
            email = f"{first.lower()}.{last.lower()}@spo.org"
            self.stdout.write(f"  {first} {last} ({email})")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nDRY RUN — no changes made. Pass --confirm to execute.")
            )
            return

        with transaction.atomic():
            self._delete_data(users_to_delete, kept_users)
            self._create_missionaries()

        self.stdout.write(self.style.SUCCESS("\nDone."))

    def _delete_data(self, users_to_delete, kept_users):
        """Delete all data for removed users, then orphan data, then the users."""
        kept_ids = set(kept_users.values_list("pk", flat=True))
        delete_ids = set(users_to_delete.values_list("pk", flat=True))

        # --- SET_NULL references pointing to users being deleted ---
        n = Solicitor.objects.filter(user_id__in=delete_ids).update(user=None)
        self.stdout.write(f"  SET_NULL Solicitor.user: {n}")
        n = Task.objects.filter(completed_by_id__in=delete_ids).update(completed_by=None)
        self.stdout.write(f"  SET_NULL Task.completed_by: {n}")
        # Event has no triggered_by — only user (CASCADE), so no SET_NULL needed
        n = JournalStageEvent.objects.filter(triggered_by_id__in=delete_ids).update(
            triggered_by=None
        )
        self.stdout.write(f"  SET_NULL JournalStageEvent.triggered_by: {n}")
        n = DecisionHistory.objects.filter(changed_by_id__in=delete_ids).update(changed_by=None)
        self.stdout.write(f"  SET_NULL DecisionHistory.changed_by: {n}")

        # --- PROTECT: GiftCredit/RecurringGiftCredit (solicitor FK is PROTECT) ---
        # Delete all gift credits first (they PROTECT solicitors)
        self._log_delete("GiftCredit", GiftCredit.objects.all())
        self._log_delete("RecurringGiftCredit", RecurringGiftCredit.objects.all())

        # --- PROTECT: Gifts/RecurringGifts -> Contact (CASCADE), but Solicitor PROTECT is cleared ---
        # Now delete all gifts (contact CASCADE will handle if we delete contacts)
        self._log_delete("Gift", Gift.objects.exclude(donor_contact__owner_id__in=kept_ids))
        self._log_delete(
            "RecurringGift", RecurringGift.objects.exclude(donor_contact__owner_id__in=kept_ids)
        )

        # --- Journal sub-models (all CASCADE from JournalContact/Journal) ---
        # NextStep, Decision, DecisionHistory, JournalStageEvent -> journal_contact -> journal -> owner
        journals_to_delete = Journal.objects.exclude(owner_id__in=kept_ids)
        jc_to_delete = JournalContact.objects.filter(journal__in=journals_to_delete)
        self._log_delete("NextStep", NextStep.objects.filter(journal_contact__in=jc_to_delete))
        self._log_delete(
            "DecisionHistory",
            DecisionHistory.objects.filter(decision__journal_contact__in=jc_to_delete),
        )
        self._log_delete("Decision", Decision.objects.filter(journal_contact__in=jc_to_delete))
        self._log_delete(
            "JournalStageEvent", JournalStageEvent.objects.filter(journal_contact__in=jc_to_delete)
        )
        self._log_delete("JournalContact", jc_to_delete)
        self._log_delete(
            "GoalJournalSelection", GoalJournalSelection.objects.filter(user_id__in=delete_ids)
        )
        self._log_delete("Journal", journals_to_delete)

        # --- PrayerIntention (CASCADE from Contact) ---
        self._log_delete(
            "PrayerIntention", PrayerIntention.objects.exclude(contact__owner_id__in=kept_ids)
        )

        # --- Event, Task (CASCADE from User or have owner FK) ---
        self._log_delete("Event", Event.objects.exclude(user_id__in=kept_ids))
        self._log_delete("Task", Task.objects.exclude(owner_id__in=kept_ids))

        # --- Legacy tables (donations, pledges) not in Django models ---
        # These FK to contacts and funds; must be cleared before those tables.
        allowed_tables = ("donations", "pledges")
        existing_tables = connection.introspection.table_names()
        with connection.cursor() as cursor:
            for table in allowed_tables:
                if table in existing_tables:
                    cursor.execute("DELETE FROM %s" % connection.ops.quote_name(table))
                    self.stdout.write(f"  Deleted legacy {table}: {cursor.rowcount}")

        # --- Contact (PROTECT from User — must delete before user) ---
        self._log_delete("Contact", Contact.objects.exclude(owner_id__in=kept_ids))

        # --- Group (CASCADE from User) ---
        self._log_delete("Group", Group.objects.exclude(owner_id__in=kept_ids))

        # --- Import models (PROTECT from User) ---
        self._log_delete(
            "ImportRowError",
            ImportRowError.objects.exclude(import_run__uploaded_by_id__in=kept_ids),
        )
        self._log_delete("ImportRun", ImportRun.objects.exclude(uploaded_by_id__in=kept_ids))
        self._log_delete("ImportBatch", ImportBatch.objects.exclude(uploaded_by_id__in=kept_ids))
        self._log_delete("MPDUpload", MPDUpload.objects.exclude(uploaded_by_id__in=kept_ids))
        self._log_delete("MPDSnapshot", MPDSnapshot.objects.filter(user_id__in=delete_ids))
        self._log_delete("MissionaryAlias", MissionaryAlias.objects.filter(user_id__in=delete_ids))

        # --- Fund (PROTECT from User, nullable owner) ---
        self._log_delete(
            "Fund", Fund.objects.filter(Q(owner_id__in=delete_ids) | Q(owner__isnull=True))
        )
        # Also delete Solicitor records with no user link
        self._log_delete("Solicitor (unlinked)", Solicitor.objects.filter(user__isnull=True))

        # --- Finally delete the users ---
        count = len(delete_ids)
        User.objects.filter(pk__in=delete_ids).delete()
        self.stdout.write(f"\n  Deleted {count} user(s)")

    def _create_missionaries(self):
        """Create the new missionary accounts."""
        self.stdout.write("\nCreating missionary accounts...")
        for first, last in MISSIONARIES:
            email = f"{first.lower()}.{last.lower()}@spo.org"
            user = User.objects.create_user(
                email=email,
                first_name=first,
                last_name=last,
                password=PASSWORD,
                role=UserRole.MISSIONARY,
                monthly_support_goal_cents=GOAL_CENTS,
                is_active=True,
            )
            self.stdout.write(f"  Created: {user.full_name} ({email})")

    def _log_delete(self, label, qs):
        count = qs.count()
        if count:
            qs.delete()
            self.stdout.write(f"  Deleted {label}: {count}")
