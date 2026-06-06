"""Resilient throttling that degrades gracefully when the cache is unavailable.

DRF's ``SimpleRateThrottle``/``ScopedRateThrottle`` read and write the default
Django cache on every throttled request. DRF runs throttle checks in
``APIView.initial()`` — before the view method is dispatched — so any error from
the cache backend turns *every* request into a 500, including a plain ``GET``
that would otherwise be a 405. The login endpoint is ``AllowAny`` and therefore
reaches the throttle before any view logic, so an unreachable cache (e.g. a
Redis instance that was deleted but whose ``REDIS_URL`` lingers in the
environment) takes authentication down entirely.

A rate limiter is best-effort defense-in-depth — django-axes provides the
authoritative, database-backed account lockout — so when the throttle's cache
backend errors out we log it and allow the request rather than failing the
whole endpoint. This is the standard "fail open" posture for rate limiting:
a degraded limiter is preferable to a hard outage.
"""

import logging

from django.core.exceptions import ImproperlyConfigured

from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle

logger = logging.getLogger(__name__)


class CacheFailOpenThrottleMixin:
    """Allow the request when the throttle's cache backend raises.

    Mix in *before* a DRF throttle class. The intent is to fail open on cache
    I/O failures (``cache.get``/``cache.set`` against an unreachable backend) so
    a cache outage cannot convert benign requests into 500s.

    Configuration errors are NOT swallowed: ``ScopedRateThrottle`` resolves and
    parses its rate inside ``allow_request`` (unlike ``SimpleRateThrottle``,
    which does so in ``__init__``), so a ``throttle_scope`` missing from
    ``DEFAULT_THROTTLE_RATES`` raises ``ImproperlyConfigured`` here. We re-raise
    that so a misconfiguration surfaces loudly instead of silently disabling
    throttling.

    Fail-open events are logged at WARNING (with the underlying error message,
    but without a per-request traceback) so a sustained outage is visible
    without flooding the logs.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except ImproperlyConfigured:
            # A missing/invalid throttle rate is a config bug, not a cache
            # outage — let it surface rather than silently allowing traffic.
            raise
        except Exception as exc:
            logger.warning(
                "Throttle cache unavailable for scope %r (%s); failing open "
                "and allowing the request.",
                getattr(self, "scope", None),
                exc,
            )
            return True


class FailOpenSimpleRateThrottle(CacheFailOpenThrottleMixin, SimpleRateThrottle):
    """``SimpleRateThrottle`` that degrades gracefully on cache failure."""


class FailOpenScopedRateThrottle(CacheFailOpenThrottleMixin, ScopedRateThrottle):
    """``ScopedRateThrottle`` that degrades gracefully on cache failure."""
