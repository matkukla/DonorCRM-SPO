"""Encrypt PrayerIntention.description.

Phase 3B (round 2). Per docs/security/data-classification.md, this column
is highly sensitive (deeply personal pastoral notes). Imports use
case-insensitive equality dedup; after encryption, the dedup callsites
(apps.imports.re_services / spo_services) load the contact's existing
intentions and Python-compare instead of issuing a SQL ``__iexact``.
"""

from django.db import migrations

import apps.core.encryption

BATCH_SIZE = 500


def reencrypt_description(apps, schema_editor):
    PrayerIntention = apps.get_model("prayers", "PrayerIntention")
    qs = (
        PrayerIntention.objects.exclude(description="")
        .exclude(description__isnull=True)
        .only("id", "description")
    )
    batch = []
    for row in qs.iterator(chunk_size=BATCH_SIZE):
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            PrayerIntention.objects.bulk_update(batch, ["description"])
            batch = []
    if batch:
        PrayerIntention.objects.bulk_update(batch, ["description"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("prayers", "0003_prayerintention_last_prayed_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="prayerintention",
            name="description",
            field=apps.core.encryption.EncryptedTextField(blank=True, verbose_name="description"),
        ),
        # Reverse is RunPython.noop — see contacts/0012 docstring.
        migrations.RunPython(reencrypt_description, migrations.RunPython.noop),
    ]
