"""Field-level encryption helpers for sensitive PII.

DonorCRM stores donor PII, gift notes, and prayer intentions as plaintext in
Postgres. At-rest encryption from Render's managed Postgres protects against
disk-level theft but NOT against:
  - A read-only DB credential leak (analytics, dump exports, snapshots)
  - A SQL-injection or ORM bug surfacing rows
  - Logical replication / read replicas in lower environments
  - Backup tarballs ending up in object storage

Field-level encryption ensures these data egress paths reveal ciphertext only.
This module provides the building blocks; field-level migration of existing
columns is a multi-phase rollout (see ``docs/security/encryption-rollout.md``).

Design
------
- Symmetric AES-GCM via ``cryptography.fernet`` for portability.
- Key material is read from ``DJANGO_PII_ENCRYPTION_KEYS`` (comma-separated
  base64-urlsafe keys). The first key is the *current* write key; remaining
  keys are *legacy* read-only keys used to decrypt rows written before a
  rotation. Adding a new key + redeploying = rotation; keys are never deleted
  until all rows have been re-encrypted under the newest key.
- ``encrypt_str`` / ``decrypt_str`` operate on UTF-8 strings.
- ``EncryptedTextField`` is a Django model field that transparently
  encrypts/decrypts on save/load. Existing fields are migrated via a
  data-migration that decrypts (no-op for plaintext) then re-encrypts.

Threat model
------------
- Defends: cold backup theft, DB credential leak, accidental SQL dump.
- Does NOT defend: an attacker with code execution on the app server (they
  hold the keys). For that, KMS-backed envelope encryption is required —
  tracked in the rollout doc as Phase 2.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Final

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

_ENV_VAR: Final = "DJANGO_PII_ENCRYPTION_KEYS"


@lru_cache(maxsize=1)
def _get_cipher() -> MultiFernet:
    """Return a process-wide MultiFernet built from the configured keys."""
    raw = getattr(settings, "PII_ENCRYPTION_KEYS", "") or ""
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise ImproperlyConfigured(
            f"PII encryption requires {_ENV_VAR} to be set "
            "(comma-separated base64-urlsafe Fernet keys). Generate one with "
            "`python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`."
        )
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt_str(plaintext: str) -> str:
    """Encrypt a UTF-8 string. Returns urlsafe base64 ciphertext."""
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        raise TypeError(f"encrypt_str requires str, got {type(plaintext).__name__}")
    return _get_cipher().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_str(ciphertext: str) -> str:
    """Decrypt a Fernet token produced by ``encrypt_str``.

    Raises ``cryptography.fernet.InvalidToken`` on tamper or unknown key.
    """
    if ciphertext is None:
        return None
    return _get_cipher().decrypt(ciphertext.encode("ascii")).decode("utf-8")


class EncryptedTextField(models.TextField):
    """TextField that transparently encrypts/decrypts on save/load.

    Storage is the urlsafe base64 ciphertext (still text). Existing plaintext
    values are detected via a sentinel-prefix check on read so a partial
    rollout doesn't crash; once all rows are migrated the fallback can be
    removed.

    Notes
    -----
    - Encrypted columns cannot be queried with ``__contains`` / ``__iexact``.
      For searchable PII keep a separate hashed-blind-index column; that is
      out of scope for this module.
    - ``null=True`` is honored: a null DB value round-trips as ``None``.
    """

    description = "Text encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256)."

    # Fernet ciphertext begins with version byte 0x80 base64-urlsafe-encoded
    # as 'gAAAAA'. We use this as a heuristic to detect already-plaintext rows
    # written before a column was migrated to EncryptedTextField.
    _CIPHERTEXT_PREFIX: Final = "gAAAAA"

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        if not value.startswith(self._CIPHERTEXT_PREFIX):
            # Legacy plaintext — return as-is so the rollout migration can
            # re-encrypt at its own pace.
            return value
        try:
            return decrypt_str(value)
        except InvalidToken:
            # Surface as a noisy error rather than silently returning ciphertext.
            raise ValueError(
                "EncryptedTextField: row decryption failed. The encryption key "
                "may have been rotated without re-encrypting this row. Check "
                f"{_ENV_VAR} configuration."
            )

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return encrypt_str(value)
