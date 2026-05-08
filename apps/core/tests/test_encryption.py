"""Tests for apps.core.encryption — AES-256-GCM field-level PII encryption.

Covers:
  * v1 (AES-256-GCM) round-trip and AEAD properties
  * legacy Fernet ciphertext is still readable when a fernet: key is configured
  * legacy plaintext passes through unchanged (rolling migration safety)
  * tamper detection
  * key rotation (aes256 → aes256, and Fernet → aes256 upgrade)
  * EncryptedTextField behavior + ORM round-trip
"""
from __future__ import annotations

import base64
import os

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

import pytest
from cryptography.fernet import Fernet

from apps.core import encryption


def _fresh_aes256_key() -> str:
    """Mint a fresh aes256:... key for use in PII_ENCRYPTION_KEYS."""
    return encryption.generate_aes256_key()


def _fresh_fernet_key() -> str:
    """Legacy Fernet key in fernet:... typed form."""
    return f"fernet:{Fernet.generate_key().decode()}"


@pytest.fixture(autouse=True)
def _reset_caches():
    encryption._clear_caches()
    yield
    encryption._clear_caches()


class TestEncryptDecrypt:
    """encrypt_str / decrypt_str round-trip behavior under AES-256-GCM."""

    def test_round_trip_ascii(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            ct = encryption.encrypt_str("hello donor")
            assert encryption.decrypt_str(ct) == "hello donor"

    def test_round_trip_unicode(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            plain = "Mëtropolis — Saint-Pierre 🙏"
            ct = encryption.encrypt_str(plain)
            assert encryption.decrypt_str(ct) == plain

    def test_ciphertext_is_versioned_and_not_plaintext(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            plain = "secret prayer intention"
            ct = encryption.encrypt_str(plain)
            assert plain not in ct
            assert ct.startswith("v1:")

    def test_two_encryptions_of_same_plaintext_differ(self):
        """AES-GCM nonce is random per write, so identical plaintexts produce
        different ciphertexts. Protects against trivial frequency analysis."""
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            ct1 = encryption.encrypt_str("same")
            ct2 = encryption.encrypt_str("same")
            assert ct1 != ct2
            assert encryption.decrypt_str(ct1) == encryption.decrypt_str(ct2) == "same"

    def test_none_passthrough(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            assert encryption.encrypt_str(None) is None
            assert encryption.decrypt_str(None) is None

    def test_encrypt_rejects_non_str(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            with pytest.raises(TypeError):
                encryption.encrypt_str(b"bytes are not str")
            with pytest.raises(TypeError):
                encryption.encrypt_str(42)

    def test_unset_keys_raises(self):
        with override_settings(PII_ENCRYPTION_KEYS=""):
            with pytest.raises(ImproperlyConfigured):
                encryption.encrypt_str("anything")

    def test_first_key_must_be_aes256(self):
        """Refusing to write under a Fernet key prevents accidental downgrade."""
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_fernet_key()):
            with pytest.raises(ImproperlyConfigured, match="first key must be aes256"):
                encryption.encrypt_str("anything")

    def test_invalid_aes256_length_rejected(self):
        # 16-byte key is AES-128, not allowed
        bad = "aes256:" + base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip("=")
        with override_settings(PII_ENCRYPTION_KEYS=bad):
            with pytest.raises(ImproperlyConfigured, match="32 bytes"):
                encryption.encrypt_str("anything")

    def test_unknown_algorithm_rejected(self):
        with override_settings(PII_ENCRYPTION_KEYS="rot13:hello"):
            with pytest.raises(ImproperlyConfigured, match="unknown key algorithm"):
                encryption.encrypt_str("anything")


class TestTamperDetection:
    def test_flipped_byte_in_ciphertext_raises(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            ct = encryption.encrypt_str("trustworthy")
            # Mutate one base64 char in the body
            head, body = ct[:3], ct[3:]
            mutated_char = "A" if body[10] != "A" else "B"
            tampered = head + body[:10] + mutated_char + body[11:]
            with pytest.raises(ValueError, match="v1 row decryption failed"):
                encryption.decrypt_str(tampered)

    def test_truncated_v1_token_raises(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            with pytest.raises(ValueError, match="too short"):
                encryption.decrypt_str("v1:AAAA")


class TestKeyRotationAES256:
    def test_old_aes256_decrypts_after_rotation(self):
        old = _fresh_aes256_key()
        new = _fresh_aes256_key()

        with override_settings(PII_ENCRYPTION_KEYS=old):
            ct_under_old = encryption.encrypt_str("legacy donor record")
        encryption._clear_caches()

        # Rotation: prepend new, keep old as read fallback.
        with override_settings(PII_ENCRYPTION_KEYS=f"{new},{old}"):
            assert encryption.decrypt_str(ct_under_old) == "legacy donor record"
            ct_under_new = encryption.encrypt_str("fresh write")
        encryption._clear_caches()

        # After old key is retired the new ciphertext still works; the old
        # one cannot. This is why rotation requires re-encrypting all rows
        # before retiring a key.
        with override_settings(PII_ENCRYPTION_KEYS=new):
            assert encryption.decrypt_str(ct_under_new) == "fresh write"
            with pytest.raises(ValueError, match="v1 row decryption failed"):
                encryption.decrypt_str(ct_under_old)


class TestLegacyFernetReadPath:
    """Rows written under the previous Fernet scheme must still decrypt."""

    def test_fernet_ciphertext_decrypts_when_fernet_key_present(self):
        fkey_typed = _fresh_fernet_key()
        fkey_raw = fkey_typed.split(":", 1)[1]
        # Write a ciphertext under the legacy scheme directly.
        legacy_ct = Fernet(fkey_raw.encode()).encrypt(b"legacy fernet row").decode()
        assert legacy_ct.startswith("gAAAAA")

        # Decrypt it via the new module with aes256 (writer) + fernet (legacy).
        new_aes = _fresh_aes256_key()
        with override_settings(PII_ENCRYPTION_KEYS=f"{new_aes},{fkey_typed}"):
            assert encryption.decrypt_str(legacy_ct) == "legacy fernet row"

    def test_fernet_ciphertext_without_fernet_key_raises(self):
        fkey_typed = _fresh_fernet_key()
        fkey_raw = fkey_typed.split(":", 1)[1]
        legacy_ct = Fernet(fkey_raw.encode()).encrypt(b"orphaned").decode()

        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            with pytest.raises(ValueError, match="no fernet: keys configured"):
                encryption.decrypt_str(legacy_ct)

    def test_unprefixed_fernet_key_treated_as_legacy_fernet(self):
        """Backwards-compat for envs still set to a bare Fernet key."""
        bare = Fernet.generate_key().decode()  # no prefix
        legacy_ct = Fernet(bare.encode()).encrypt(b"compat").decode()
        new_aes = _fresh_aes256_key()
        with override_settings(PII_ENCRYPTION_KEYS=f"{new_aes},{bare}"):
            assert encryption.decrypt_str(legacy_ct) == "compat"


class TestGenerateAES256Key:
    def test_format(self):
        k = encryption.generate_aes256_key()
        assert k.startswith("aes256:")
        material = k.split(":", 1)[1]
        # 32 bytes urlsafe-base64 unpadded = 43 chars
        assert len(material) == 43
        decoded = base64.urlsafe_b64decode(material + "=")
        assert len(decoded) == 32

    def test_unique(self):
        assert encryption.generate_aes256_key() != encryption.generate_aes256_key()


class TestEncryptedTextField:
    def test_get_prep_value_encrypts_to_v1(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            field = encryption.EncryptedTextField()
            stored = field.get_prep_value("donor address line")
            assert stored != "donor address line"
            assert stored.startswith("v1:")

    def test_get_prep_value_passthrough_empty(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            field = encryption.EncryptedTextField()
            assert field.get_prep_value("") == ""
            assert field.get_prep_value(None) is None

    def test_from_db_value_decrypts_v1(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            field = encryption.EncryptedTextField()
            ct = encryption.encrypt_str("from the wire")
            assert field.from_db_value(ct, None, None) == "from the wire"

    def test_from_db_value_decrypts_legacy_fernet(self):
        fkey_typed = _fresh_fernet_key()
        fkey_raw = fkey_typed.split(":", 1)[1]
        legacy_ct = Fernet(fkey_raw.encode()).encrypt(b"legacy row").decode()
        with override_settings(PII_ENCRYPTION_KEYS=f"{_fresh_aes256_key()},{fkey_typed}"):
            field = encryption.EncryptedTextField()
            assert field.from_db_value(legacy_ct, None, None) == "legacy row"

    def test_from_db_value_returns_legacy_plaintext_unchanged(self):
        """Critical for rolling migration: rows written before column was
        encrypted read as plaintext until the data migration runs."""
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            field = encryption.EncryptedTextField()
            assert field.from_db_value("plain pre-migration", None, None) == "plain pre-migration"

    def test_from_db_value_passthrough_empty(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            field = encryption.EncryptedTextField()
            assert field.from_db_value(None, None, None) is None
            assert field.from_db_value("", None, None) == ""

    def test_from_db_value_raises_on_retired_key(self):
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            ct = encryption.encrypt_str("data under retired key")
        encryption._clear_caches()
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            field = encryption.EncryptedTextField()
            with pytest.raises(ValueError, match="v1 row decryption failed"):
                field.from_db_value(ct, None, None)


@pytest.mark.django_db
class TestContactNotesEncryption:
    """Integration test: Contact.notes round-trips through the ORM."""

    def test_round_trip_via_orm(self, user_factory):
        from apps.contacts.models import Contact

        owner = user_factory()
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            encryption._clear_caches()
            contact = Contact.objects.create(
                owner=owner,
                first_name="Alice",
                last_name="Donor",
                notes="High capacity, prefers email contact, met at 2026 retreat",
            )
            fetched = Contact.objects.get(pk=contact.pk)
            assert fetched.notes == "High capacity, prefers email contact, met at 2026 retreat"

    def test_blank_notes_round_trip(self, user_factory):
        from apps.contacts.models import Contact

        owner = user_factory()
        with override_settings(PII_ENCRYPTION_KEYS=_fresh_aes256_key()):
            encryption._clear_caches()
            contact = Contact.objects.create(owner=owner, first_name="A", last_name="B", notes="")
            assert Contact.objects.get(pk=contact.pk).notes == ""
