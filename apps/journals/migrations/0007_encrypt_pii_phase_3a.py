"""Encrypt JournalStageEvent.notes at rest.

Phase 3A of the encryption rollout. Same pattern as
contacts.0012_encrypt_pii_phase_3a — see that migration's docstring for the
sequence and safety notes.
"""

from django.db import migrations

import apps.core.encryption

BATCH_SIZE = 500


def reencrypt_notes(apps, schema_editor):
    Event = apps.get_model("journals", "JournalStageEvent")
    qs = Event.objects.exclude(notes="").exclude(notes__isnull=True).only("id", "notes")
    batch = []
    for ev in qs.iterator(chunk_size=BATCH_SIZE):
        batch.append(ev)
        if len(batch) >= BATCH_SIZE:
            Event.objects.bulk_update(batch, ["notes"])
            batch = []
    if batch:
        Event.objects.bulk_update(batch, ["notes"])


def decrypt_notes(apps, schema_editor):
    Event = apps.get_model("journals", "JournalStageEvent")
    qs = Event.objects.exclude(notes="").exclude(notes__isnull=True).only("id", "notes")
    batch = []
    for ev in qs.iterator(chunk_size=BATCH_SIZE):
        batch.append(ev)
        if len(batch) >= BATCH_SIZE:
            Event.objects.bulk_update(batch, ["notes"])
            batch = []
    if batch:
        Event.objects.bulk_update(batch, ["notes"])


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("journals", "0006_journalcontact_journal_con_contact_b9c00f_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="journalstageevent",
            name="notes",
            field=apps.core.encryption.EncryptedTextField(
                blank=True, help_text="Optional notes about this event", verbose_name="notes"
            ),
        ),
        migrations.RunPython(reencrypt_notes, decrypt_notes),
    ]
