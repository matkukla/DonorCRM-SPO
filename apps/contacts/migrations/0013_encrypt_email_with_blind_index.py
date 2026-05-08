"""Encrypt Contact.email and add HMAC blind-index sidecar.

Phase 3B of the encryption rollout. After this migration:

  * Contact.email is stored as AES-256-GCM ciphertext.
  * Contact.email_hash holds HMAC-SHA256(BLIND_INDEX_KEY, normalized(email))
    used by services and import dedup for equality lookups.
  * The email-uniqueness constraint moves from (owner, email) plaintext to
    (owner, email_hash) — same uniqueness semantics, computed from
    deterministic hashes.
  * The DRF SearchFilter no longer matches partial emails (no substring
    search on encrypted columns). Callers must hash the search query and
    look up email_hash explicitly.

Sequence:
  1. Add nullable email_hash column.
  2. RunPython A: backfill email_hash from plaintext email (still readable
     because AlterField hasn't run yet — model state has EmailField).
  3. Drop old email-based constraint + index.
  4. AlterField email -> EncryptedTextField (no DB op; both map to TEXT/varchar).
  5. RunPython B: re-save every row so plaintext on disk becomes v1
     ciphertext (the from_db_value legacy fallback returns plaintext on
     read; bulk_update -> get_prep_value encrypts on write).
  6. Add email_hash index + new unique constraint.

Safety:
  * atomic = False so each batch commits independently.
  * Both data steps are idempotent.
  * If BLIND_INDEX_KEYS or PII_ENCRYPTION_KEYS is unset, RunPython A or B
    raises ImproperlyConfigured at the first row. Set the env vars and
    rerun.
"""

from django.db import migrations, models

import apps.core.encryption

BATCH_SIZE = 500


def backfill_email_hash(apps, schema_editor):
    """RunPython A: compute email_hash for every existing contact."""
    from apps.core.blind_index import hash_value

    Contact = apps.get_model("contacts", "Contact")
    qs = Contact.objects.exclude(email="").exclude(email__isnull=True).only("id", "email")
    batch = []
    for c in qs.iterator(chunk_size=BATCH_SIZE):
        c.email_hash = hash_value(c.email)
        batch.append(c)
        if len(batch) >= BATCH_SIZE:
            Contact.objects.bulk_update(batch, ["email_hash"])
            batch = []
    if batch:
        Contact.objects.bulk_update(batch, ["email_hash"])


def clear_email_hash(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    Contact.objects.update(email_hash=None)


def reencrypt_email(apps, schema_editor):
    """RunPython B: rewrite plaintext email values as v1 ciphertext."""
    Contact = apps.get_model("contacts", "Contact")
    qs = Contact.objects.exclude(email="").exclude(email__isnull=True).only("id", "email")
    batch = []
    for c in qs.iterator(chunk_size=BATCH_SIZE):
        # Reading c.email returned plaintext via the legacy fallback in
        # EncryptedTextField.from_db_value. Writing it back through bulk_update
        # invokes get_prep_value, which encrypts under the current write key.
        batch.append(c)
        if len(batch) >= BATCH_SIZE:
            Contact.objects.bulk_update(batch, ["email"])
            batch = []
    if batch:
        Contact.objects.bulk_update(batch, ["email"])


def decrypt_email(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    qs = Contact.objects.exclude(email="").exclude(email__isnull=True).only("id", "email")
    batch = []
    for c in qs.iterator(chunk_size=BATCH_SIZE):
        batch.append(c)
        if len(batch) >= BATCH_SIZE:
            Contact.objects.bulk_update(batch, ["email"])
            batch = []
    if batch:
        Contact.objects.bulk_update(batch, ["email"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("contacts", "0012_encrypt_pii_phase_3a"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="email_hash",
            field=models.BinaryField(blank=True, null=True, verbose_name="email hash"),
        ),
        # Backfill BEFORE we drop the old index/constraint and BEFORE the
        # AlterField — at this point the model state still has email as a
        # plain EmailField, so c.email returns plaintext.
        migrations.RunPython(backfill_email_hash, clear_email_hash),
        migrations.RemoveConstraint(
            model_name="contact",
            name="unique_contact_email_per_owner",
        ),
        migrations.RemoveIndex(
            model_name="contact",
            name="contacts_email_2eb381_idx",
        ),
        migrations.AlterField(
            model_name="contact",
            name="email",
            field=apps.core.encryption.EncryptedTextField(blank=True, verbose_name="email"),
        ),
        # Re-encrypt every existing email under the current write key.
        migrations.RunPython(reencrypt_email, decrypt_email),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(fields=["email_hash"], name="contacts_email_h_7c5d3c_idx"),
        ),
        migrations.AddConstraint(
            model_name="contact",
            constraint=models.UniqueConstraint(
                condition=models.Q(("email_hash__isnull", False), ("is_merged", False)),
                fields=("owner", "email_hash"),
                name="unique_contact_email_per_owner",
            ),
        ),
    ]
