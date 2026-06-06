"""HMAC-SHA256 blind-index helper for encrypted equality lookups.

When a column is encrypted with ``EncryptedTextField`` the database sees
only ciphertext, so SQL equality (``__iexact``, ``__exact``) and unique
constraints stop working. The standard remedy is a sidecar column holding
``HMAC-SHA256(BLIND_INDEX_KEY, normalized(value))`` and indexing/querying
on that hash instead of the plaintext.

Threat model
------------
The blind-index key (``DJANGO_BLIND_INDEX_KEYS``) lives separately from the
PII encryption keys (``DJANGO_PII_ENCRYPTION_KEYS``) because the security
properties differ:

  * Compromise of the blind-index key alone enables an attacker holding a
    DB dump to perform *targeted* equality lookups (e.g. "is alice@x.com
    in the table?") via known-plaintext hash computation. They cannot
    enumerate values, decrypt rows, or recover plaintext.
  * Without the key, the column is uniform 32-byte values with no
    extractable structure beyond which rows have identical plaintext
    (the same equality leak any deterministic encryption has).

Key custody best practice: keep the two key sets in different vault items
and grant access independently.

Rotation
--------
Format: ``DJANGO_BLIND_INDEX_KEYS=key1[,key2[,key3]]`` where each key is
32 raw bytes urlsafe-base64-encoded (with or without ``=`` padding).
The first key is the *current write key*. Remaining keys are read-only
fallbacks used by ``lookup_hashes`` so queries during a rotation window
match rows hashed under either key.

Rotation procedure:
  1. Mint a new key with ``generate_blind_index_key()``.
  2. Prepend it: ``DJANGO_BLIND_INDEX_KEYS=<new>,<old>``. Redeploy.
  3. Run a re-hash sweep (re-save every row) so all rows hash under the
     new key.
  4. Remove the old key from the env var, redeploy.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from functools import lru_cache
from typing import Final, List, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

_ENV_VAR: Final = "DJANGO_BLIND_INDEX_KEYS"
_KEY_LEN: Final = 32  # SHA-256 / HMAC key length


def _b64url_decode(data: str) -> bytes:
    pad = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + ("=" * pad))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_blind_index_key() -> str:
    """Mint a fresh 32-byte blind-index key (urlsafe-base64, no padding)."""
    return _b64url_encode(os.urandom(_KEY_LEN))


def _parse_keys() -> List[bytes]:
    raw = getattr(settings, "BLIND_INDEX_KEYS", "") or ""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ImproperlyConfigured(
            f"Blind index requires {_ENV_VAR} (comma-separated, first entry "
            "is the current write key). Mint one with "
            '`python -c "from apps.core.blind_index import generate_blind_index_key; '
            'print(generate_blind_index_key())"`.'
        )
    out: List[bytes] = []
    for entry in parts:
        decoded = _b64url_decode(entry)
        if len(decoded) != _KEY_LEN:
            raise ImproperlyConfigured(
                f"{_ENV_VAR}: each key must decode to {_KEY_LEN} bytes, "
                f"got {len(decoded)} for entry."
            )
        out.append(decoded)
    return out


@lru_cache(maxsize=1)
def _get_keys() -> Tuple[bytes, ...]:
    return tuple(_parse_keys())


def _normalize(value: str) -> str:
    """Canonicalize a string before hashing.

    Lowercases via ``casefold`` (Unicode-aware) and strips outer whitespace
    so case/whitespace variants of the same value collide. Callers that
    need different normalization (e.g. phone-number digit extraction) can
    pre-process before passing the value in.
    """
    return value.strip().casefold()


def hash_value(value: str | None) -> bytes | None:
    """Compute the blind-index hash for storage under the current write key.

    Returns ``None`` for ``None`` or empty input (so a NULL/empty plaintext
    column has a NULL/empty hash column, preserving conditional-unique
    semantics).
    """
    if value is None or value == "":
        return None
    key = _get_keys()[0]
    return hmac.new(key, _normalize(value).encode("utf-8"), hashlib.sha256).digest()


def lookup_hashes(value: str | None) -> List[bytes]:
    """Compute hashes under *all* configured keys for read-time queries.

    During a key rotation, some rows are still hashed under the previous
    key. ``Model.objects.filter(email_hash__in=lookup_hashes(query))`` finds
    rows under either key.
    """
    if value is None or value == "":
        return []
    norm = _normalize(value).encode("utf-8")
    return [hmac.new(k, norm, hashlib.sha256).digest() for k in _get_keys()]


_PHONE_NON_DIGIT_RE = re.compile(r"\D")


def normalize_phone(value: str | None) -> str | None:
    """Strip non-digit characters from a phone number for blind-indexing.

    Same digit string from "(555) 123-4567", "555-123-4567", "+1 555 123 4567",
    "5551234567" — all hash to the same value. Returns ``None`` for empty /
    no-digit input so the caller skips the index column for blank rows.
    """
    if not value:
        return None
    digits = _PHONE_NON_DIGIT_RE.sub("", value)
    return digits or None


def _clear_caches() -> None:
    """Reset memoization. Test-only helper."""
    _get_keys.cache_clear()


class BinaryHashField(models.BinaryField):
    """BinaryField that always returns ``bytes`` (never ``memoryview``).

    psycopg2's BYTEA adapter returns ``memoryview`` for binary columns,
    which silently fails Python equality against ``bytes``:

        contact.email_hash == hash_value(email)   # False even when equal!

    ORM ``__in`` filters work fine because psycopg2 handles the
    comparison in SQL. This subclass is for the Python-side path: any
    caller comparing the hash via ``==`` gets a ``bytes`` result so the
    comparison works as expected.

    Schema-wise this is identical to ``BinaryField``; the override is
    purely a Python-side type guarantee.
    """

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return bytes(value)
