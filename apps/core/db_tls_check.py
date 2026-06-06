"""Startup verification of the Postgres TLS posture.

Runs once after Django starts to confirm:
  * The connection is encrypted (``ssl IS on``).
  * The negotiated TLS version is 1.2 or 1.3.
  * The cipher and bits are recorded so the audit log captures evidence.

Failures behavior:
  * In production: a non-TLS or sub-1.2 connection raises at startup,
    refusing to serve requests.
  * In dev/test (SQLite, or non-prod settings): the check is a no-op.

Logged via ``apps.core.audit.audit_event`` so the result is grep-able next to
auth and crypto events.
"""

from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.db import connection

from apps.core.audit import audit_event

_MIN_TLS_VERSION = ("TLSv1.2", "TLSv1.3")


def verify_db_tls(strict: bool = True) -> Optional[dict]:
    """Query the live DB connection for its TLS state.

    Returns a dict with ``version``, ``cipher``, ``bits``, and ``ssl`` keys
    when running on Postgres; ``None`` for non-Postgres (e.g. SQLite test DB).

    Raises ``RuntimeError`` if ``strict`` is True and the connection is not
    using TLS 1.2+.
    """
    if connection.vendor != "postgresql":
        return None

    # pg_stat_ssl is the canonical source for the live backend's TLS state.
    # Available in Postgres 9.5+. The row matches the current backend pid.
    with connection.cursor() as cur:
        cur.execute(
            "SELECT ssl, version, cipher, bits FROM pg_stat_ssl " "WHERE pid = pg_backend_pid()"
        )
        row = cur.fetchone()

    if not row:
        info = {"ssl": None, "version": None, "cipher": None, "bits": None}
    else:
        ssl_on, version, cipher, bits = row
        info = {"ssl": bool(ssl_on), "version": version, "cipher": cipher, "bits": bits}

    audit_event("db.tls.check", **info)

    if strict:
        if not info["ssl"]:
            raise RuntimeError(
                "DB connection is not using TLS. Set DB_SSLMODE=require (or "
                "stricter) and ensure the Postgres server accepts TLS."
            )
        if info["version"] not in _MIN_TLS_VERSION:
            raise RuntimeError(
                f"DB TLS version {info['version']!r} is below the minimum "
                f"({_MIN_TLS_VERSION}). Upgrade the Postgres server or pin "
                "the client min_protocol_version."
            )
    return info


def maybe_verify_at_startup() -> None:
    """Hook called from CoreConfig.ready() in production-like envs.

    Checks ``DJANGO_SETTINGS_MODULE`` so dev/test don't pay this cost.
    Failures are raised so a misconfigured deploy fails its health check
    rather than silently serving over a non-TLS link.
    """
    settings_mod = getattr(settings, "SETTINGS_MODULE", "") or ""
    if not settings_mod.endswith(".prod"):
        return
    verify_db_tls(strict=True)
