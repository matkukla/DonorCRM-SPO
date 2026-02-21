"""
Data migration: Copy Donation -> Gift and Pledge -> RecurringGift.

Preserves UUIDs, converts Decimal amounts to cents, and maps
legacy frequency/status values to the new RE-compatible enum values.
"""
from django.db import migrations


def migrate_donations_to_gifts(apps, schema_editor):
    """Copy all Donation records to Gift records with field mapping."""
    Donation = apps.get_model('donations', 'Donation')
    Gift = apps.get_model('gifts', 'Gift')

    batch = []
    for d in Donation.objects.all().iterator(chunk_size=1000):
        batch.append(Gift(
            id=d.id,
            donor_contact_id=d.contact_id,
            fund_id=d.fund_id,
            external_gift_id=d.external_id or '',
            amount_cents=int(d.amount * 100),
            gift_date=d.date,
            description=d.notes or '',
            created_at=d.created_at,
            updated_at=d.updated_at,
        ))
        if len(batch) >= 1000:
            Gift.objects.bulk_create(batch, batch_size=1000, ignore_conflicts=True)
            batch = []

    if batch:
        Gift.objects.bulk_create(batch, batch_size=1000, ignore_conflicts=True)


def migrate_pledges_to_recurring_gifts(apps, schema_editor):
    """Copy all Pledge records to RecurringGift records with field mapping."""
    Pledge = apps.get_model('pledges', 'Pledge')
    RecurringGift = apps.get_model('gifts', 'RecurringGift')

    # Map legacy frequency/status values to new RE-compatible values
    FREQ_MAP = {
        'semi_annual': 'semi_annually',
        'annual': 'annually',
    }
    STATUS_MAP = {
        'paused': 'held',
    }

    batch = []
    for p in Pledge.objects.all().iterator(chunk_size=1000):
        batch.append(RecurringGift(
            id=p.id,
            donor_contact_id=p.contact_id,
            fund_id=p.fund_id,
            external_gift_id=p.external_id or '',
            amount_cents=int(p.amount * 100),
            frequency=FREQ_MAP.get(p.frequency, p.frequency),
            status=STATUS_MAP.get(p.status, p.status),
            start_date=p.start_date,
            end_date=p.end_date,
            description=p.notes or '',
            created_at=p.created_at,
            updated_at=p.updated_at,
        ))
        if len(batch) >= 1000:
            RecurringGift.objects.bulk_create(
                batch, batch_size=1000, ignore_conflicts=True,
            )
            batch = []

    if batch:
        RecurringGift.objects.bulk_create(
            batch, batch_size=1000, ignore_conflicts=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('gifts', '0002_alter_solicitor_user'),
        ('donations', '0004_add_fund_fk'),
        ('pledges', '0003_add_external_id_and_fund'),
    ]

    operations = [
        migrations.RunPython(
            migrate_donations_to_gifts,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            migrate_pledges_to_recurring_gifts,
            migrations.RunPython.noop,
        ),
    ]
