"""
Management command to backfill Gift records for existing RecurringGift commitments.

For each RecurringGift, generates a Gift record per payment period from
start_date through min(end_date, today). Uses deterministic external_gift_id
for idempotency.
"""
from django.core.management.base import BaseCommand

from apps.gifts.models import Gift, RecurringGift, RecurringGiftFrequency
from apps.gifts.recurring_utils import (
    generate_gifts_for_recurring,
    generate_payment_dates,
    make_recurring_external_id,
)
from apps.gifts.signals import disable_gift_signals, enable_gift_signals


class Command(BaseCommand):
    help = "Generate Gift records for existing RecurringGift commitments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            type=str,
            default=None,
            help="Only process recurring gifts with this status (e.g., active)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without actually creating records",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        status_filter = options["status"]

        qs = RecurringGift.objects.exclude(
            frequency=RecurringGiftFrequency.IRREGULAR,
        ).select_related("donor_contact")

        if status_filter:
            qs = qs.filter(status=status_filter)

        total_rgs = qs.count()
        self.stdout.write(f"Processing {total_rgs} recurring gift(s)...")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no records will be created"))

        total_created = 0
        total_skipped = 0
        contacts_updated = set()

        disable_gift_signals()
        try:
            for rg in qs.iterator():
                if dry_run:
                    dates = generate_payment_dates(
                        rg.start_date,
                        rg.end_date,
                        rg.frequency,
                    )
                    rg_ext_id = rg.external_gift_id or str(rg.pk)
                    ext_ids = [
                        make_recurring_external_id(rg_ext_id, pd, rg.frequency) for pd in dates
                    ]
                    existing = (
                        Gift.objects.filter(external_gift_id__in=ext_ids).count() if ext_ids else 0
                    )
                    would_create = len(dates) - existing
                    self.stdout.write(
                        f"  {rg} — {len(dates)} period(s), {would_create} new payment(s)"
                    )
                    total_created += would_create
                else:
                    created = generate_gifts_for_recurring(rg)
                    if created > 0:
                        contacts_updated.add(rg.donor_contact_id)
                        total_created += created
                    else:
                        total_skipped += 1
        finally:
            enable_gift_signals()

        # Update contact stats for all affected contacts
        if not dry_run and contacts_updated:
            from apps.contacts.models import Contact

            for contact in Contact.objects.filter(pk__in=contacts_updated):
                contact.update_giving_stats()

        self.stdout.write(
            self.style.SUCCESS(
                f'{"Would create" if dry_run else "Created"} {total_created} gift record(s), '
                f"skipped {total_skipped} (already exist), "
                f"updated {len(contacts_updated)} contact(s)"
            )
        )
