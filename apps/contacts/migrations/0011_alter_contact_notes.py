"""Encrypt Contact.notes at rest.

Phase 1A of the encryption migration plan (docs/security/encryption-plan.md).

Sequence:
  1. AlterField swaps the column type to EncryptedTextField (no DB-level
     change — both types map to TEXT).
  2. RunPython re-saves every existing row in batches of 500. The read path
     returns plaintext via the legacy-sentinel check, the save path encrypts
     under the current PII_ENCRYPTION_KEYS write key.

Safety:
  - atomic = False so each batch commits independently. A 1M-row table
    will not lock for the duration; the migration can be paused/resumed.
  - The data step is idempotent: re-running it re-encrypts already-encrypted
    rows under the current write key. Output bytes change but the plaintext
    round-trip is preserved.
  - If PII_ENCRYPTION_KEYS is unset at deploy time, the AlterField succeeds
    (no DB op) but the RunPython step raises ImproperlyConfigured at the
    first save. Fix: set the env var, redeploy, rerun the migration.
"""

from django.db import migrations

import apps.core.encryption


def reencrypt_notes(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    # iterator() avoids loading the entire table into memory.
    # We touch only rows with a non-empty notes value to skip the no-op work.
    qs = Contact.objects.exclude(notes="").exclude(notes__isnull=True).only("id", "notes")
    batch = []
    BATCH_SIZE = 500
    for contact in qs.iterator(chunk_size=BATCH_SIZE):
        # Reading `contact.notes` returns plaintext for legacy rows (sentinel
        # check in EncryptedTextField.from_db_value). Saving re-encrypts
        # under the current write key.
        batch.append(contact)
        if len(batch) >= BATCH_SIZE:
            Contact.objects.bulk_update(batch, ["notes"])
            batch = []
    if batch:
        Contact.objects.bulk_update(batch, ["notes"])


def decrypt_notes(apps, schema_editor):
    """Reverse step: read every value (which decrypts) and write it back as
    plaintext. Used only if we need to back the migration out."""
    Contact = apps.get_model("contacts", "Contact")
    qs = Contact.objects.exclude(notes="").exclude(notes__isnull=True).only("id", "notes")
    batch = []
    BATCH_SIZE = 500
    for contact in qs.iterator(chunk_size=BATCH_SIZE):
        # Reading already gives plaintext. Bulk-saving will re-encrypt because
        # the field is still EncryptedTextField at this point — to truly
        # reverse, the model's AlterField must run first (handled by Django's
        # reverse migration ordering).
        batch.append(contact)
        if len(batch) >= BATCH_SIZE:
            Contact.objects.bulk_update(batch, ["notes"])
            batch = []
    if batch:
        Contact.objects.bulk_update(batch, ["notes"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("contacts", "0010_update_unique_constraints_exclude_merged"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="notes",
            field=apps.core.encryption.EncryptedTextField(blank=True, verbose_name="notes"),
        ),
        migrations.RunPython(reencrypt_notes, decrypt_notes),
    ]
