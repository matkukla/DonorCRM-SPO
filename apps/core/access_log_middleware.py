"""Middleware that records PII-touching requests to ``DataAccessLog``.

Every request whose path matches a configured pattern (donor PII or
financial-context endpoints) gets one row in the access log: who, when,
what method, what path, status code, and — for retrieve endpoints — the
resource id parsed from the URL.

Design choices
--------------
- **One row per request, post-response.** We attach the row in
  ``process_response`` so we can record the status code and have the
  request body fully consumed.
- **Pattern-based, not view-introspecting.** Middleware doesn't need a
  per-view registry; the URL is the contract. New PII endpoints get
  added to ``_PII_PATH_PATTERNS`` below.
- **Fail-open.** If the log write fails for any reason, the request still
  succeeds — observability isn't worth a 500. Failures emit an
  ``audit_event("access_log.write_failed", ...)`` so they're noticeable.
- **No request body inspection.** The path + method are enough; reading
  request bodies would risk ingesting PII into the audit log itself.
"""

from __future__ import annotations

import logging
import re
from typing import Final

from django.utils.deprecation import MiddlewareMixin

from apps.core.audit import audit_event

logger = logging.getLogger("security.audit")

# Path prefixes that warrant a DataAccessLog entry. Order doesn't matter;
# all are tested. Keep regex anchored at start of path for performance.
#
# Capture group ``rid`` extracts the leaf resource UUID for retrieve/update/
# delete endpoints. List endpoints have no ``rid`` and are recorded with
# resource_id="".
_PII_PATH_PATTERNS: Final = [
    (
        "Contact",
        re.compile(r"^/api/v1/contacts/(?:(?P<rid>[0-9a-f-]{36})/?)?(?:[a-z_/-]*)?$"),
    ),
    (
        "Gift",
        re.compile(r"^/api/v1/gifts/(?:(?P<rid>[0-9a-f-]{36})/?)?(?:[a-z_/-]*)?$"),
    ),
    (
        "RecurringGift",
        re.compile(r"^/api/v1/recurring-gifts/(?:(?P<rid>[0-9a-f-]{36})/?)?(?:[a-z_/-]*)?$"),
    ),
    (
        "Journal",
        re.compile(r"^/api/v1/journals?/(?:(?P<rid>[0-9a-f-]{36})/?)?(?:[a-z_/-]*)?$"),
    ),
    (
        "JournalContact",
        re.compile(r"^/api/v1/journal-(?:members|contacts)/(?:(?P<rid>[0-9a-f-]{36})/?)?$"),
    ),
    (
        "PrayerIntention",
        re.compile(r"^/api/v1/prayer-intentions/(?:(?P<rid>[0-9a-f-]{36})/?)?(?:[a-z_/-]*)?$"),
    ),
    (
        "ImportExport",
        # Bulk PII egress is the highest-risk read path; always log it.
        re.compile(r"^/api/v1/imports/(?:contacts/export|generic/export|.*?/export)/?$"),
    ),
]

# Skip these even if they match a sensitive prefix — they're not PII reads.
_SKIP_PATH_PATTERNS: Final = [
    re.compile(r"^/api/v1/health/?$"),
    re.compile(r"^/api/v1/auth/"),  # auth has its own audit channel
]


def _classify(path: str) -> tuple[str, str]:
    """Return (resource_type, resource_id) for a path, or ("", "") if not PII.

    resource_id is empty for list endpoints; populated when the URL contains
    a leaf UUID.
    """
    for skip in _SKIP_PATH_PATTERNS:
        if skip.match(path):
            return "", ""
    for resource_type, pattern in _PII_PATH_PATTERNS:
        m = pattern.match(path)
        if m:
            return resource_type, m.groupdict().get("rid", "") or ""
    return "", ""


class DataAccessLogMiddleware(MiddlewareMixin):
    """Insert a DataAccessLog row for every PII-touching request."""

    def process_response(self, request, response):
        try:
            self._maybe_log(request, response)
        except Exception as exc:  # pragma: no cover — fail-open
            audit_event("access_log.write_failed", error=str(exc), path=request.path)
        return response

    def _maybe_log(self, request, response) -> None:
        path = request.path or ""
        resource_type, resource_id = _classify(path)
        if not resource_type:
            return

        # Defer the import so the middleware module doesn't pull models at
        # Django startup before the apps registry is ready.
        from apps.core.models import DataAccessLog

        actor = getattr(request, "user", None)
        actor_id = getattr(actor, "id", None) if (actor and actor.is_authenticated) else None
        view_as_user = getattr(request, "view_as_user", None)

        # Best-effort row count for list endpoints: DRF stuffs the paginator
        # into response.data; not all responses have it.
        row_count = 0
        if not resource_id and hasattr(response, "data") and isinstance(response.data, dict):
            count = response.data.get("count")
            if isinstance(count, int):
                row_count = count

        ua = (request.META.get("HTTP_USER_AGENT") or "")[:256]
        ip = request.META.get("REMOTE_ADDR")

        DataAccessLog.objects.create(
            actor=actor if actor_id else None,
            actor_id_snapshot=actor_id,
            view_as_user=view_as_user if getattr(view_as_user, "pk", None) else None,
            method=request.method or "",
            path=path[:512],
            resource_type=resource_type,
            resource_id=resource_id,
            row_count=row_count,
            ip=ip,
            user_agent=ua,
            status_code=response.status_code,
        )
