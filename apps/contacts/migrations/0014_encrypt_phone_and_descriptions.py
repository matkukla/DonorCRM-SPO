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
  2. RunPython: backfill both hashes AND re-encrypt phone, while phone
     is still a plain CharField in the historical model state. Reading
     c.phone returns plaintext directly; bulk_update writes ciphertext
     once the AlterField swap (step 3) takes effect.
  3. AlterField phone -> EncryptedTextField (column type swap is a no-op
     at the storage layer; both map to TEXT/varchar in Postgres).

The previous version inverted steps 2 and 3, relying on
``decrypt_str``'s legacy plaintext fallback to handle the historical
model state. That worked but was semantically fragile: tightening the
fallback would silently break the migration. The current ordering does
not depend on the fallback.

Note: this migration intentionally does NOT re-alter email_hash. The
named index on email_hash is created in 0013; the previous redundant
AlterField with db_index=True caused Postgres to maintain a duplicate
auto-generated B-tree index for the same column.
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
        # phone is still a plain CharField in this RunPython's model state
        # (the AlterField below has not run yet), so c.phone is plaintext.
        # phone_secondary was migrated in 3A but on-disk values may still be
        # plaintext until rotate_pii_encryption sweeps; from_db_value's
        # legacy fallback returns plaintext in that case as well.
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
        # Backfill BEFORE AlterField so the historical model still has phone
        # as a plain CharField (returns plaintext directly, no decrypt path).
        # Reverse is RunPython.noop because reading + bulk_update would
        # re-encrypt under a new nonce, not decrypt.
        migrations.RunPython(
            backfill_phone_hashes_and_reencrypt, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="contact",
            name="phone",
            field=apps.core.encryption.EncryptedTextField(blank=True, verbose_name="phone"),
        ),
    ]
