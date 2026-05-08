"""Encrypt Contact.phone and add phone_hash / phone_secondary_hash sidecars.

Phase 3B (round 2). After this migration:

  * Contact.phone is stored as AES-256-GCM ciphertext.
  * Contact.phone_hash and Contact.phone_secondary_hash hold
    HMAC-SHA256(BLIND_INDEX_KEY, digits_only(value)) for equality dedup.
  * Substring phone search (`__icontains`) is no longer supported on either
    column; full-number lookup via the blind index still works.
  * Fixes a Phase 3A regression where ``Contact.phone_secondary=value``
    silently returned 0 rows because the column was already encrypted but
    no blind index existed.

Sequence:
  1. Add nullable phone_hash + phone_secondary_hash columns.
  2. RunPython: backfill both hashes (and re-encrypt phone).
  3. AlterField phone -> EncryptedTextField.

Notes:
  * email_hash is also re-altered here only because the AddField above
    forced an ordering recompute. The semantics are unchanged.
"""

from django.db import migrations, models

import apps.core.encryption

BATCH_SIZE = 500


def backfill_phone_hashes_and_reencrypt(apps, schema_editor):
    from apps.core.blind_index import hash_value, normalize_phone

    Contact = apps.get_model("contacts", "Contact")
    qs = Contact.objects.only("id", "phone", "phone_secondary").iterator(chunk_size=BATCH_SIZE)
    batch = []
    for c in qs:
        # Reading c.phone returns plaintext (still CharField in this model state).
        # Reading c.phone_secondary returns plaintext via from_db_value
        # legacy fallback even though the column was migrated in 3A — until
        # the rotate command sweeps the table, on-disk values can still be
        # plaintext.
        c.phone_hash = hash_value(normalize_phone(c.phone))
        c.phone_secondary_hash = hash_value(normalize_phone(c.phone_secondary))
        batch.append(c)
        if len(batch) >= BATCH_SIZE:
            Contact.objects.bulk_update(batch, ["phone", "phone_hash", "phone_secondary_hash"])
            batch = []
    if batch:
        Contact.objects.bulk_update(batch, ["phone", "phone_hash", "phone_secondary_hash"])


def clear_phone_hashes(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    Contact.objects.update(phone_hash=None, phone_secondary_hash=None)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("contacts", "0013_encrypt_email_with_blind_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="phone_hash",
            field=models.BinaryField(
                blank=True, db_index=True, null=True, verbose_name="phone hash"
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="phone_secondary_hash",
            field=models.BinaryField(
                blank=True, db_index=True, null=True, verbose_name="phone secondary hash"
            ),
        ),
        migrations.AlterField(
            model_name="contact",
            name="email_hash",
            field=models.BinaryField(
                blank=True, db_index=True, null=True, verbose_name="email hash"
            ),
        ),
        migrations.AlterField(
            model_name="contact",
            name="phone",
            field=apps.core.encryption.EncryptedTextField(blank=True, verbose_name="phone"),
        ),
        # Both writes happen inside one batch loop so we visit each row once.
        migrations.RunPython(backfill_phone_hashes_and_reencrypt, clear_phone_hashes),
    ]
