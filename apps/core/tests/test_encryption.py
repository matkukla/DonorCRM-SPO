"""Tests for apps.core.encryption — field-level PII encryption."""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

import pytest
from cryptography.fernet import Fernet, InvalidToken

from apps.core import encryption


def _fresh_key() -> str:
    return Fernet.generate_key().decode()


def _clear_cipher_cache() -> None:
    """The MultiFernet cipher is lru_cached; reset between settings overrides."""
    encryption._get_cipher.cache_clear()


@pytest.fixture(autouse=True)
def _reset_cipher():
    _clear_cipher_cache()
    yield
    _clear_cipher_cache()


class TestEncryptDecrypt:
    """encrypt_str / decrypt_str round-trip behavior."""

    def test_round_trip_ascii(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            ct = encryption.encrypt_str("hello donor")
            assert encryption.decrypt_str(ct) == "hello donor"

    def test_round_trip_unicode(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            plain = "Mëtropolis — Saint-Pierre 🙏"
            ct = encryption.encrypt_str(plain)
            assert encryption.decrypt_str(ct) == plain

    def test_ciphertext_is_not_plaintext(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            plain = "secret prayer intention"
            ct = encryption.encrypt_str(plain)
            assert plain not in ct
            assert ct.startswith(encryption.EncryptedTextField._CIPHERTEXT_PREFIX)

    def test_two_encryptions_of_same_plaintext_differ(self):
        """Fernet ciphertext includes a random IV, so identical plaintexts
        produce different ciphertexts each call. This is a fundamental AEAD
        property and protects against trivial frequency analysis."""
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            ct1 = encryption.encrypt_str("same")
            ct2 = encryption.encrypt_str("same")
            assert ct1 != ct2
            assert encryption.decrypt_str(ct1) == encryption.decrypt_str(ct2) == "same"

    def test_none_passthrough(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            assert encryption.encrypt_str(None) is None
            assert encryption.decrypt_str(None) is None

    def test_encrypt_rejects_non_str(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            with pytest.raises(TypeError):
                encryption.encrypt_str(b"bytes are not str")
            with pytest.raises(TypeError):
                encryption.encrypt_str(42)

    def test_unset_keys_raises(self):
        with override_settings(PII_ENCRYPTION_KEYS=""):
            with pytest.raises(ImproperlyConfigured):
                encryption.encrypt_str("anything")


class TestKeyRotation:
    """MultiFernet decrypts under any historical key but encrypts under the first."""

    def test_old_ciphertext_decrypts_after_rotation(self):
        old_key = _fresh_key()
        new_key = _fresh_key()

        with override_settings(PII_ENCRYPTION_KEYS=old_key):
            ct_under_old = encryption.encrypt_str("legacy donor record")
        _clear_cipher_cache()

        # Rotation: prepend the new key, keep the old as a read fallback.
        with override_settings(PII_ENCRYPTION_KEYS=f"{new_key},{old_key}"):
            assert encryption.decrypt_str(ct_under_old) == "legacy donor record"
            ct_under_new = encryption.encrypt_str("fresh write")
        _clear_cipher_cache()

        # After old key is retired, the new ciphertext still works; the old
        # one no longer can be read (which is why we must re-encrypt all rows
        # before retiring a key).
        with override_settings(PII_ENCRYPTION_KEYS=new_key):
            assert encryption.decrypt_str(ct_under_new) == "fresh write"
            with pytest.raises(InvalidToken):
                encryption.decrypt_str(ct_under_old)


class TestEncryptedTextField:
    """Field-level transparent encryption for Django models."""

    def test_get_prep_value_encrypts(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            field = encryption.EncryptedTextField()
            stored = field.get_prep_value("donor address line")
            assert stored != "donor address line"
            assert stored.startswith("gAAAAA")

    def test_get_prep_value_passthrough_empty(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            field = encryption.EncryptedTextField()
            assert field.get_prep_value("") == ""
            assert field.get_prep_value(None) is None

    def test_from_db_value_decrypts_ciphertext(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            field = encryption.EncryptedTextField()
            ct = encryption.encrypt_str("from the wire")
            assert field.from_db_value(ct, None, None) == "from the wire"

    def test_from_db_value_returns_legacy_plaintext_unchanged(self):
        """Critical for the rolling-migration story: rows written before the
        column was migrated read as plaintext until the data migration runs."""
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            field = encryption.EncryptedTextField()
            assert field.from_db_value("plain pre-migration", None, None) == "plain pre-migration"

    def test_from_db_value_passthrough_empty(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            field = encryption.EncryptedTextField()
            assert field.from_db_value(None, None, None) is None
            assert field.from_db_value("", None, None) == ""

    def test_from_db_value_raises_on_unknown_key(self):
        """If a row was encrypted under a key no longer in PII_ENCRYPTION_KEYS,
        we must fail loudly rather than silently return ciphertext to the
        application layer."""
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            ct = encryption.encrypt_str("data under retired key")
        _clear_cipher_cache()
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            field = encryption.EncryptedTextField()
            with pytest.raises(ValueError, match="row decryption failed"):
                field.from_db_value(ct, None, None)


@pytest.mark.django_db
class TestContactNotesEncryption:
    """Integration test: Contact.notes round-trips through the ORM."""

    def test_round_trip_via_orm(self, user_factory):
        from apps.contacts.models import Contact

        owner = user_factory()
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            _clear_cipher_cache()
            contact = Contact.objects.create(
                owner=owner,
                first_name="Alice",
                last_name="Donor",
                notes="High capacity, prefers email contact, met at 2026 retreat",
            )
            # Refetch from DB to prove the value round-tripped through PG.
            fetched = Contact.objects.get(pk=contact.pk)
            assert fetched.notes == "High capacity, prefers email contact, met at 2026 retreat"

    def test_blank_notes_round_trip(self, user_factory):
        from apps.contacts.models import Contact

        owner = user_factory()
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_key()):
            _clear_cipher_cache()
            contact = Contact.objects.create(owner=owner, first_name="A", last_name="B", notes="")
            assert Contact.objects.get(pk=contact.pk).notes == ""
