"""Field-level encryption helpers for sensitive PII (AES-256-GCM).

DonorCRM stores donor PII, gift notes, and prayer intentions as plaintext in
Postgres. At-rest encryption from Render's managed Postgres protects against
disk-level theft but NOT against:
  - A read-only DB credential leak (analytics, dump exports, snapshots)
  - A SQL-injection or ORM bug surfacing rows
  - Logical replication / read replicas in lower environments
  - Backup tarballs ending up in object storage

Field-level encryption ensures these data egress paths reveal ciphertext only.

Design
------
- AES-256-GCM (NIST SP 800-38D, AEAD). 32-byte key, 12-byte random nonce,
  16-byte authentication tag appended to ciphertext by the cryptography lib.
- Storage format (text): ``v1:<base64-urlsafe(nonce || ciphertext_with_tag)>``.
  The unpadded ``v1:`` prefix is a versioning marker that enables forward
  migration to v2 (KMS-wrapped DEKs) without breaking reads of v1 rows.
- Key material is read from ``DJANGO_PII_ENCRYPTION_KEYS`` (comma-separated).
  Each entry is typed:
      ``aes256:<base64_urlsafe_32_bytes>`` — AES-256 key (current scheme)
      ``fernet:<fernet_key>``              — legacy Fernet key (read-only)
      ``<value_no_prefix>``                — treated as Fernet (legacy env)
  The first key is the *current write key* and MUST be ``aes256:``.
  Remaining keys are *legacy read-only* keys used to decrypt rows written
  before a rotation. Generate a fresh write key with::

      python -c "from apps.core.encryption import generate_aes256_key; print(generate_aes256_key())"

- Legacy Fernet ciphertext (starts with ``gAAAAA``) is decrypted under any
  configured ``fernet:`` key for backward compatibility during the rollout.
  The ``rotate_pii_encryption`` management command re-encrypts rows under
  the current AES-256-GCM write key.

Threat model
------------
- Defends: cold backup theft, DB credential leak, accidental SQL dump.
- Does NOT defend: an attacker with code execution on the app server (they
  hold the keys). For that, KMS-backed envelope encryption is required —
  tracked as Phase 5 in ``docs/security/encryption-rollout.md``.
"""
from __future__ import annotations

import base64
import os
from functools import lru_cache
from typing import Final, List, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_ENV_VAR: Final = "DJANGO_PII_ENCRYPTION_KEYS"

# Storage prefixes — outside the base64 payload so detection is unambiguous
# regardless of plaintext contents.
_V1_PREFIX: Final = "v1:"

# Fernet's binary token starts with version byte 0x80, which encodes to
# ``gAAAAA`` in URL-safe base64 (the next chars come from the timestamp);
# a stable detection prefix for legacy ciphertext.
_FERNET_PREFIX: Final = "gAAAAA"

# AES-GCM nonce length. NIST SP 800-38D §8.2 recommends 96 bits (12 bytes).
_NONCE_LEN: Final = 12

# AES-GCM authentication tag length (appended to ciphertext by AESGCM.encrypt).
_TAG_LEN: Final = 16


def _b64url_decode(data: str) -> bytes:
    """Base64-urlsafe decode, accepting unpadded input."""
    pad = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + ("=" * pad))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_aes256_key() -> str:
    """Generate a fresh AES-256 key formatted for ``PII_ENCRYPTION_KEYS``.

    Returns ``aes256:<32-byte-urlsafe-base64>`` suitable for the
    comma-separated env var.
    """
    return f"aes256:{_b64url_encode(os.urandom(32))}"


class _KeyMaterial:
    """Parsed encryption key with its algorithm tag."""

    __slots__ = ("algo", "raw")

    def __init__(self, algo: str, raw: bytes) -> None:
        self.algo = algo  # "aes256" or "fernet"
        self.raw = raw


def _parse_keys() -> List[_KeyMaterial]:
    """Read PII_ENCRYPTION_KEYS into a typed key list (write key first).

    Format per entry:
      aes256:<base64_urlsafe_32_bytes>   -> AES-256-GCM key
      fernet:<fernet_key>                -> Fernet key (legacy, read-only)
      <value_no_prefix>                  -> assumed Fernet (legacy env compat)
    """
    raw = getattr(settings, "PII_ENCRYPTION_KEYS", "") or ""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ImproperlyConfigured(
            f"PII encryption requires {_ENV_VAR} to be set (comma-separated, "
            "first entry must be aes256:<base64-32-bytes>). Mint one with "
            '`python -c "from apps.core.encryption import generate_aes256_key; '
            'print(generate_aes256_key())"`.'
        )

    keys: List[_KeyMaterial] = []
    for entry in parts:
        if ":" in entry:
            algo, material = entry.split(":", 1)
            algo = algo.lower()
        else:
            algo, material = "fernet", entry  # legacy unprefixed Fernet

        if algo == "aes256":
            decoded = _b64url_decode(material)
            if len(decoded) != 32:
                raise ImproperlyConfigured(
                    f"{_ENV_VAR}: aes256 key must decode to 32 bytes, " f"got {len(decoded)}."
                )
            keys.append(_KeyMaterial("aes256", decoded))
        elif algo == "fernet":
            try:
                Fernet(material.encode("ascii"))  # validate
            except (ValueError, TypeError) as exc:
                raise ImproperlyConfigured(f"{_ENV_VAR}: invalid Fernet key — {exc}") from exc
            keys.append(_KeyMaterial("fernet", material.encode("ascii")))
        else:
            raise ImproperlyConfigured(
                f"{_ENV_VAR}: unknown key algorithm {algo!r}. " "Expected aes256 or fernet."
            )
    return keys


@lru_cache(maxsize=1)
def _get_keys() -> Tuple[_KeyMaterial, ...]:
    return tuple(_parse_keys())


@lru_cache(maxsize=1)
def _get_write_aesgcm() -> AESGCM:
    """AESGCM cipher for the current write key. First key MUST be aes256."""
    head = _get_keys()[0]
    if head.algo != "aes256":
        raise ImproperlyConfigured(
            f"{_ENV_VAR}: first key must be aes256: (current write algorithm). "
            "Add an aes256 key to the front of the list and redeploy. "
            "Mint one with apps.core.encryption.generate_aes256_key()."
        )
    return AESGCM(head.raw)


@lru_cache(maxsize=1)
def _get_legacy_fernet() -> MultiFernet | None:
    fernet_keys = [Fernet(k.raw) for k in _get_keys() if k.algo == "fernet"]
    if not fernet_keys:
        return None
    return MultiFernet(fernet_keys)


def _all_aes256_keys() -> List[bytes]:
    return [k.raw for k in _get_keys() if k.algo == "aes256"]


def encrypt_str(plaintext: str | None) -> str | None:
    """Encrypt a UTF-8 string with AES-256-GCM. Returns ``v1:<base64>``."""
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        raise TypeError(f"encrypt_str requires str, got {type(plaintext).__name__}")
    aesgcm = _get_write_aesgcm()
    nonce = os.urandom(_NONCE_LEN)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return _V1_PREFIX + _b64url_encode(nonce + ct)


def decrypt_str(token: str | None) -> str | None:
    """Decrypt a token produced by ``encrypt_str`` (any historical version).

    Dispatches by storage prefix:
      * ``v1:`` — AES-256-GCM, tries each configured aes256 key
      * ``gAAAAA`` — legacy Fernet, decrypted via configured fernet keys
      * anything else — treated as legacy plaintext and returned as-is
    """
    if token is None:
        return None

    if token.startswith(_V1_PREFIX):
        blob = _b64url_decode(token[len(_V1_PREFIX) :])
        if len(blob) < _NONCE_LEN + _TAG_LEN:
            raise ValueError("EncryptedTextField: v1 token too short for nonce + tag.")
        nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
        aes_keys = _all_aes256_keys()
        if not aes_keys:
            raise ValueError(
                "EncryptedTextField: v1 ciphertext encountered but no aes256 keys "
                f"configured in {_ENV_VAR}."
            )
        for key in aes_keys:
            try:
                return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")
            except InvalidTag:
                continue
        raise ValueError(
            "EncryptedTextField: v1 row decryption failed under all configured "
            f"aes256 keys. Check {_ENV_VAR} — a key may have been rotated out "
            "without re-encrypting this row."
        )

    if token.startswith(_FERNET_PREFIX):
        legacy = _get_legacy_fernet()
        if legacy is None:
            raise ValueError(
                "EncryptedTextField: legacy Fernet ciphertext found but no "
                f"fernet: keys configured. Add the legacy key to {_ENV_VAR} "
                "or run rotate_pii_encryption to upgrade rows to v1."
            )
        try:
            return legacy.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken as e:
            raise ValueError(
                "EncryptedTextField: legacy Fernet row decryption failed. "
                f"Check {_ENV_VAR} — the original key may no longer be present."
            ) from e

    # Legacy plaintext (column not yet migrated). Return as-is so a partial
    # rollout doesn't crash; the rotation command re-encrypts at its pace.
    return token


def _clear_caches() -> None:
    """Reset memoization. Test-only helper."""
    _get_keys.cache_clear()
    _get_write_aesgcm.cache_clear()
    _get_legacy_fernet.cache_clear()


class EncryptedTextField(models.TextField):
    """TextField that transparently encrypts/decrypts on save/load.

    Storage is ``v1:<base64-urlsafe>`` (AES-256-GCM) for new writes. Reads
    transparently handle legacy Fernet ciphertext (``gAAAAA`` prefix) and
    legacy plaintext so a rolling migration does not crash before all rows
    are re-encrypted.

    Notes
    -----
    - Encrypted columns cannot be queried with ``__contains`` / ``__iexact``.
      For searchable PII keep a separate hashed-blind-index column.
    - ``null=True`` is honored: a null DB value round-trips as ``None``.
    """

    description = "Text encrypted at rest with AES-256-GCM (v1) — see apps.core.encryption."

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return decrypt_str(value)

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return encrypt_str(value)


# Compatibility shim for legacy callers that referenced ``encryption._get_cipher``
# (e.g. older test fixtures). New code should call ``_clear_caches()``.
class _CipherCacheCompat:
    @staticmethod
    def cache_clear() -> None:
        _clear_caches()


_get_cipher = _CipherCacheCompat()
