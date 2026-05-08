"""Encrypt Gift.description and RecurringGift.description.

Phase 3B (round 2). Same pattern as contacts.0011/0012/journals.0007:
AlterField swaps the column to EncryptedTextField; RunPython re-saves every
non-empty row so the on-disk value becomes v1 ciphertext.
"""

from django.db import migrations

import apps.core.encryption

BATCH_SIZE = 500


def reencrypt_descriptions(apps, schema_editor):
    Gift = apps.get_model("gifts", "Gift")
    RecurringGift = apps.get_model("gifts", "RecurringGift")
    for Model in (Gift, RecurringGift):
        qs = (
            Model.objects.exclude(description="")
            .exclude(description__isnull=True)
            .only("id", "description")
        )
        batch = []
        for row in qs.iterator(chunk_size=BATCH_SIZE):
            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                Model.objects.bulk_update(batch, ["description"])
                batch = []
        if batch:
            Model.objects.bulk_update(batch, ["description"])


def decrypt_descriptions(apps, schema_editor):
    reencrypt_descriptions(apps, schema_editor)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("gifts", "0007_recurring_gift_payment_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gift",
            name="description",
            field=apps.core.encryption.EncryptedTextField(blank=True, verbose_name="description"),
        ),
        migrations.AlterField(
            model_name="recurringgift",
            name="description",
            field=apps.core.encryption.EncryptedTextField(blank=True, verbose_name="description"),
        ),
        migrations.RunPython(reencrypt_descriptions, decrypt_descriptions),
    ]
