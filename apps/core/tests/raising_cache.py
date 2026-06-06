"""A cache backend that raises on every operation.

Used by throttle-resilience tests to simulate an unreachable cache (e.g. a
deleted Redis instance) deterministically, without depending on a real server
or network timing. Point ``CACHES["default"]["BACKEND"]`` at this class via
``override_settings`` to reproduce the production failure mode.
"""

from django.core.cache.backends.base import BaseCache


class CacheUnavailable(Exception):
    """Stand-in for a backend connection error (e.g. redis ConnectionError)."""


class RaisingCache(BaseCache):
    def __init__(self, server, params):
        super().__init__(params)

    def _fail(self, *args, **kwargs):
        raise CacheUnavailable("simulated cache backend outage")

    # Cover every method DRF throttles may touch.
    get = _fail
    set = _fail
    add = _fail
    delete = _fail
    incr = _fail
    touch = _fail
