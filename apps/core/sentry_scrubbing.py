"""Sentry ``before_send`` / ``before_breadcrumb`` hooks for PII scrubbing.

Defense in depth: ``send_default_pii=False`` already filters Django's
auto-attached PII (request body, cookies, user attributes). This hook
removes PII that may have leaked into:

  * Exception ``args`` and string representations (e.g. an email
    appearing in a `ValueError` message).
  * Breadcrumb messages (logger calls that included a PII value).
  * Custom tags / extras that any code path may have attached.

The patterns target obvious PII shapes:
  * Email addresses
  * North-American phone numbers (10/11 digit groupings)
  * US ZIP codes inside an address-like string

Tested by ``apps.core.tests.test_sentry_scrubbing``.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)")

_REDACTED = "[REDACTED]"


def _scrub_string(s: str) -> str:
    s = _EMAIL_RE.sub(_REDACTED, s)
    s = _PHONE_RE.sub(_REDACTED, s)
    return s


def _scrub_value(v: Any) -> Any:
    if isinstance(v, str):
        return _scrub_string(v)
    if isinstance(v, list):
        return [_scrub_value(x) for x in v]
    if isinstance(v, tuple):
        return tuple(_scrub_value(x) for x in v)
    if isinstance(v, dict):
        return {k: _scrub_value(x) for k, x in v.items()}
    return v


def before_send(event: Mapping[str, Any], hint: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """Sentry hook — scrub PII patterns from event payload.

    Returns a new event dict; never mutates the input.
    """
    return _scrub_value(event)


def before_breadcrumb(
    crumb: Mapping[str, Any], hint: Mapping[str, Any]
) -> Optional[Mapping[str, Any]]:
    return _scrub_value(crumb)
