"""Sentry ``before_send`` / ``before_breadcrumb`` hooks for PII scrubbing.

Defense in depth: ``send_default_pii=False`` already filters Django's
auto-attached PII (request body, cookies, user attributes). This hook
removes PII that may have leaked into:

  * Exception ``args`` and string representations (e.g. an email
    appearing in a `ValueError` message).
  * Breadcrumb messages (logger calls that included a PII value).
  * Custom tags / extras that any code path may have attached.
  * Stack frame local variables (Sentry attaches frame ``vars`` for
    every captured exception). Includes locals stored in sets and
    arbitrary Python objects, which are coerced through ``repr()``
    before scrubbing.

The patterns target obvious PII shapes:
  * Email addresses
  * North-American phone numbers (10/11 digit groupings)

Tested by ``apps.core.tests.test_sentry_scrubbing``.
"""

from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)")

_REDACTED = "[REDACTED]"

# Cap on repr() length for unknown objects. Sentry rejects oversized
# event payloads; truncating before scrubbing also prevents pathological
# __repr__ implementations from blowing up the hook.
_REPR_MAX_LEN = 1024


def _scrub_string(s: str) -> str:
    s = _EMAIL_RE.sub(_REDACTED, s)
    s = _PHONE_RE.sub(_REDACTED, s)
    return s


def _scrub_value(v: Any) -> Any:
    """Recursively scrub PII patterns from JSON-shaped Python values.

    Handles dict / list / tuple / str natively. Sets and frozensets are
    scrubbed element-wise (returned as a sorted list since Sentry's JSON
    serializer cannot encode sets directly). Anything else is coerced
    through ``repr()`` and string-scrubbed so a stray PII value held in
    a custom object's ``__repr__`` does not slip past the regex pass.

    The function never mutates its argument.
    """
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return _scrub_string(v)
    if isinstance(v, dict):
        return {k: _scrub_value(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_scrub_value(x) for x in v]
    if isinstance(v, tuple):
        return tuple(_scrub_value(x) for x in v)
    if isinstance(v, (set, frozenset)):
        # Sentry's JSON serializer can't encode sets; serialize as a
        # sorted list of scrubbed reprs so output is deterministic.
        return sorted(_scrub_value(x) for x in v)
    # Bytes / bytearrays / memoryviews — best-effort utf-8 decode then
    # scrub; fall through to repr if decoding fails.
    if isinstance(v, (bytes, bytearray, memoryview)):
        try:
            decoded = bytes(v).decode("utf-8")
        except UnicodeDecodeError:
            return _scrub_string(repr(bytes(v))[:_REPR_MAX_LEN])
        return _scrub_string(decoded)
    # Arbitrary object — never let a stray PII value sneak through via a
    # custom ``__repr__``. Cap the length so a pathological repr can't
    # explode event size.
    try:
        return _scrub_string(repr(v)[:_REPR_MAX_LEN])
    except Exception:  # noqa: BLE001 — defensive fallback for hostile reprs
        return f"<unrepresentable {type(v).__name__}>"


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Sentry hook — scrub PII patterns from event payload.

    Returns a new event dict; never mutates the input. The scrubber
    walks ``exception.values[].stacktrace.frames[].vars`` because Sentry
    attaches frame locals there for every captured exception.
    """
    return _scrub_value(event)


def before_breadcrumb(crumb: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    return _scrub_value(crumb)
