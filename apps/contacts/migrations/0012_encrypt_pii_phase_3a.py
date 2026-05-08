"""Encrypt Contact.phone_secondary and Contact.street_address at rest.

Phase 3A of the encryption rollout (docs/security/encryption-rollout.md).

Sequence per field:
  1. AlterField swaps the column type to EncryptedTextField. The DDL drops
     the VARCHAR length cap (now TEXT) but Postgres handles existing rows
     in place — no row rewrite from the DDL alone.
  2. RunPython re-saves every row with a non-empty value. The read path
     returns plaintext via the legacy fallback in EncryptedTextField,
     and the save path encrypts under the current write key.

Safety:
  - atomic = False so each batch commits independently. The migration is
    pause/resume-safe.
  - The data step is idempotent: re-running re-encrypts already-encrypted
    rows (different nonce, same plaintext on read).
  - If PII_ENCRYPTION_KEYS is unset at deploy time, AlterField succeeds
    (no DB op) but the RunPython step raises ImproperlyConfigured at the
    first save. Fix: set the env var, redeploy, rerun the migration.
"""

from django.db import migrations

import apps.core.encryption

BATCH_SIZE = 500
_FIELDS = ["phone_secondary", "street_address"]


def reencrypt_phase_3a(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    for field_name in _FIELDS:
        qs = (
            Contact.objects.exclude(**{field_name: ""})
            .exclude(**{f"{field_name}__isnull": True})
            .only("id", field_name)
        )
        batch = []
        for contact in qs.iterator(chunk_size=BATCH_SIZE):
            batch.append(contact)
            if len(batch) >= BATCH_SIZE:
                Contact.objects.bulk_update(batch, [field_name])
                batch = []
        if batch:
            Contact.objects.bulk_update(batch, [field_name])


def decrypt_phase_3a(apps, schema_editor):
    """Reverse step. See note in 0011_alter_contact_notes about reversibility."""
    Contact = apps.get_model("contacts", "Contact")
    for field_name in _FIELDS:
        qs = (
            Contact.objects.exclude(**{field_name: ""})
            .exclude(**{f"{field_name}__isnull": True})
            .only("id", field_name)
        )
        batch = []
        for contact in qs.iterator(chunk_size=BATCH_SIZE):
            batch.append(contact)
            if len(batch) >= BATCH_SIZE:
                Contact.objects.bulk_update(batch, [field_name])
                batch = []
        if batch:
            Contact.objects.bulk_update(batch, [field_name])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("contacts", "0011_alter_contact_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="phone_secondary",
            field=apps.core.encryption.EncryptedTextField(
                blank=True, verbose_name="secondary phone"
            ),
        ),
        migrations.AlterField(
            model_name="contact",
            name="street_address",
            field=apps.core.encryption.EncryptedTextField(
                blank=True, verbose_name="street address"
            ),
        ),
        migrations.RunPython(reencrypt_phase_3a, decrypt_phase_3a),
    ]
