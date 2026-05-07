"""Structured security audit log.

Wraps a dedicated logger (``security.audit``) so that security-relevant
events (login success/failure, role changes, lockouts, exports of bulk data,
view-as activations) are emitted in one place with consistent fields.

Why a dedicated channel:
- Filterable in log aggregators (Sentry breadcrumbs, GCP/AWS log insights).
- A retention/forwarding policy can be applied to it independently of app logs.
- Keeps PII discipline localized — never log password, JWT, or full email here.

Usage::

    from apps.core.audit import audit_event

    audit_event(
        "auth.login.success",
        actor_id=user.id,
        ip=request.META.get("REMOTE_ADDR"),
    )
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("security.audit")


def audit_event(event: str, **fields: Any) -> None:
    """Emit a structured INFO-level audit event.

    ``event`` is a dotted slug like ``auth.login.failure`` or
    ``export.contacts.csv``. ``fields`` are flat key/value pairs serialized
    as ``key=value`` for easy grep/log-query parsing.

    Never pass raw passwords, tokens, or unfiltered request bodies here.
    """
    parts = [f"event={event}"]
    for k, v in fields.items():
        if v is None:
            continue
        # Quote values containing spaces or '=' so the line stays parseable.
        s = str(v)
        if " " in s or "=" in s:
            s = f'"{s}"'
        parts.append(f"{k}={s}")
    logger.info(" ".join(parts))
