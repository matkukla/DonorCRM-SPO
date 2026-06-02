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

from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle

logger = logging.getLogger(__name__)


class CacheFailOpenThrottleMixin:
    """Allow the request when the throttle's cache backend raises.

    Mix in *before* a DRF throttle class. Only cache I/O inside
    ``allow_request`` is expected to raise here (rate parsing happens in
    ``__init__``); on any such failure we fail open so a cache outage cannot
    convert benign requests into 500s. The error is logged at WARNING with a
    traceback so the outage is never silent.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            logger.warning(
                "Throttle cache unavailable for scope %r; failing open and "
                "allowing the request.",
                getattr(self, "scope", None),
                exc_info=True,
            )
            return True


class FailOpenSimpleRateThrottle(CacheFailOpenThrottleMixin, SimpleRateThrottle):
    """``SimpleRateThrottle`` that degrades gracefully on cache failure."""


class FailOpenScopedRateThrottle(CacheFailOpenThrottleMixin, ScopedRateThrottle):
    """``ScopedRateThrottle`` that degrades gracefully on cache failure."""
