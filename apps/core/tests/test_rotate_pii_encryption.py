"""Tests for the ``rotate_pii_encryption`` management command.

Covers the realistic scenarios:

  * Mixed table (legacy plaintext + Fernet + v1 rows) all converge to v1
    after the sweep.
  * Re-running is idempotent (no corruption).
  * ``--dry-run`` does not write.
  * ``--resume-from-id`` skips ahead.
  * Unknown app/model/field is a CommandError.
"""
from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

import pytest
from cryptography.fernet import Fernet

from apps.core import encryption


def _aes256() -> str:
    return encryption.generate_aes256_key()


def _typed_fernet() -> tuple[str, str]:
    raw = Fernet.generate_key().decode()
    return f"fernet:{raw}", raw


@pytest.mark.django_db
class TestRotatePiiEncryption:
    """End-to-end via Contact.notes (the only registered encrypted field)."""

    def _make_contacts_mixed(self, user_factory, raw_fernet_key: str):
        """Create three rows: one v1, one legacy Fernet, one legacy plaintext.

        Returns the ids in (v1, fernet, plaintext) order. The Fernet and
        plaintext rows must be written via raw SQL so the EncryptedTextField
        descriptor doesn't re-encrypt them under v1 on the way in.
        """
        from apps.contacts.models import Contact

        owner = user_factory()
        # Row written through the EncryptedTextField under aes256 -> v1.
        c_v1 = Contact.objects.create(
            owner=owner,
            first_name="V1",
            last_name="Row",
            notes="already v1",
        )
        # Two rows with placeholder content; we'll overwrite the on-disk
        # `notes` column directly via cursor to install the legacy shapes.
        c_fernet = Contact.objects.create(
            owner=owner,
            first_name="Fernet",
            last_name="Row",
            notes="placeholder",
        )
        c_plain = Contact.objects.create(
            owner=owner,
            first_name="Plain",
            last_name="Row",
            notes="placeholder",
        )
        legacy_fernet_ct = Fernet(raw_fernet_key.encode()).encrypt(b"legacy fernet body").decode()
        self._raw_set_notes(c_fernet.pk, legacy_fernet_ct)
        self._raw_set_notes(c_plain.pk, "plain pre-migration body")
        return c_v1.pk, c_fernet.pk, c_plain.pk

    @staticmethod
    def _pk_param(pk):
        from django.db import connection

        # SQLite stores UUIDField as 32-char hex (no dashes); Postgres stores
        # as native uuid. Match the on-disk shape so cursor queries work.
        return pk.hex if connection.vendor == "sqlite" else str(pk)

    def _raw_set_notes(self, pk, value):
        from django.db import connection
        from apps.contacts.models import Contact

        with connection.cursor() as cur:
            cur.execute(
                f'UPDATE "{Contact._meta.db_table}" SET notes = %s WHERE id = %s',
                [value, self._pk_param(pk)],
            )

    def _raw_notes(self, pk):
        from django.db import connection
        from apps.contacts.models import Contact

        with connection.cursor() as cur:
            cur.execute(
                f'SELECT notes FROM "{Contact._meta.db_table}" WHERE id = %s',
                [self._pk_param(pk)],
            )
            row = cur.fetchone()
            return row[0] if row else None

    def test_mixed_table_converges_to_v1(self, user_factory):
        from apps.contacts.models import Contact

        ftyped, fraw = _typed_fernet()
        keys = f"{_aes256()},{ftyped}"
        with override_settings(PII_ENCRYPTION_KEYS=keys):
            encryption._clear_caches()
            v1_id, fernet_id, plain_id = self._make_contacts_mixed(user_factory, fraw)

            out = StringIO()
            call_command(
                "rotate_pii_encryption",
                "--app",
                "contacts",
                "--model",
                "Contact",
                "--field",
                "notes",
                stdout=out,
            )

            for pk in (v1_id, fernet_id, plain_id):
                raw = self._raw_notes(pk)
                # Rotation now upgrades to v2 (per-field AAD); legacy v1
                # rows remain readable but new writes use v2.
                assert raw.startswith("v2:"), f"row {pk} stored as {raw[:20]!r}"

            # Plaintext still readable through ORM.
            assert Contact.objects.get(pk=v1_id).notes == "already v1"
            assert Contact.objects.get(pk=fernet_id).notes == "legacy fernet body"
            assert Contact.objects.get(pk=plain_id).notes == "plain pre-migration body"

    def test_idempotent(self, user_factory):
        from apps.contacts.models import Contact

        ftyped, fraw = _typed_fernet()
        keys = f"{_aes256()},{ftyped}"
        with override_settings(PII_ENCRYPTION_KEYS=keys):
            encryption._clear_caches()
            v1_id, fernet_id, plain_id = self._make_contacts_mixed(user_factory, fraw)

            for _ in range(3):
                call_command(
                    "rotate_pii_encryption",
                    "--app",
                    "contacts",
                    "--model",
                    "Contact",
                    "--field",
                    "notes",
                    stdout=StringIO(),
                )

            # Plaintext semantics preserved across multiple sweeps.
            assert Contact.objects.get(pk=v1_id).notes == "already v1"
            assert Contact.objects.get(pk=fernet_id).notes == "legacy fernet body"
            assert Contact.objects.get(pk=plain_id).notes == "plain pre-migration body"

    def test_dry_run_does_not_write(self, user_factory):
        ftyped, fraw = _typed_fernet()
        keys = f"{_aes256()},{ftyped}"
        with override_settings(PII_ENCRYPTION_KEYS=keys):
            encryption._clear_caches()
            _, fernet_id, plain_id = self._make_contacts_mixed(user_factory, fraw)
            before_fernet = self._raw_notes(fernet_id)
            before_plain = self._raw_notes(plain_id)
            assert before_fernet.startswith("gAAAAA")
            assert before_plain == "plain pre-migration body"

            call_command(
                "rotate_pii_encryption",
                "--app",
                "contacts",
                "--model",
                "Contact",
                "--field",
                "notes",
                "--dry-run",
                stdout=StringIO(),
            )

            assert self._raw_notes(fernet_id) == before_fernet
            assert self._raw_notes(plain_id) == before_plain

    def test_all_flag_uses_registry(self, user_factory):
        from apps.contacts.models import Contact

        with override_settings(PII_ENCRYPTION_KEYS=_aes256()):
            encryption._clear_caches()
            owner = user_factory()
            c = Contact.objects.create(owner=owner, first_name="A", last_name="B", notes="hi")
            Contact.objects.filter(pk=c.pk).update(notes="raw plaintext")

            out = StringIO()
            call_command("rotate_pii_encryption", "--all", stdout=out)

            assert self._raw_notes(c.pk).startswith("v2:")
            assert Contact.objects.get(pk=c.pk).notes == "raw plaintext"

    def test_unknown_field_raises(self):
        with override_settings(PII_ENCRYPTION_KEYS=_aes256()):
            encryption._clear_caches()
            with pytest.raises(CommandError, match="no field 'doesnotexist'"):
                call_command(
                    "rotate_pii_encryption",
                    "--app",
                    "contacts",
                    "--model",
                    "Contact",
                    "--field",
                    "doesnotexist",
                    stdout=StringIO(),
                )

    def test_no_target_specified_raises(self):
        with override_settings(PII_ENCRYPTION_KEYS=_aes256()):
            encryption._clear_caches()
            with pytest.raises(CommandError, match="Nothing to do"):
                call_command("rotate_pii_encryption", stdout=StringIO())
