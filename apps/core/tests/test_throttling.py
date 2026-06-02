"""Tests for cache-resilient (fail-open) throttling.

These verify that a cache outage degrades rate limiting to "allow" instead of
turning throttled endpoints into 500s, while normal throttling still works when
the cache is healthy.
"""
from unittest.mock import Mock

from django.core.cache.backends.locmem import LocMemCache
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APIRequestFactory

import pytest

from apps.core.tests.raising_cache import CacheUnavailable
from apps.core.throttling import FailOpenScopedRateThrottle, FailOpenSimpleRateThrottle

# Point the default cache at a backend that raises on every operation,
# reproducing an unreachable Redis (the production failure mode).
RAISING_CACHE = {"default": {"BACKEND": "apps.core.tests.raising_cache.RaisingCache"}}

factory = APIRequestFactory()


class _SimpleAuthThrottle(FailOpenSimpleRateThrottle):
    scope = "auth"  # 5/min in DEFAULT_THROTTLE_RATES

    def get_cache_key(self, request, view):
        return "throttle_test_fixed_key"


class _ScopedView:
    throttle_scope = "feedback"  # 20/hour in DEFAULT_THROTTLE_RATES


class TestFailOpenSimpleRateThrottle:
    def test_allows_request_when_cache_raises(self, caplog):
        throttle = _SimpleAuthThrottle()
        throttle.cache = Mock()
        throttle.cache.get.side_effect = CacheUnavailable("boom")

        request = factory.get("/api/v1/auth/login/")
        with caplog.at_level("WARNING"):
            allowed = throttle.allow_request(request, view=None)

        assert allowed is True
        assert "failing open" in caplog.text.lower()

    def test_still_enforces_limit_with_working_cache(self):
        throttle = _SimpleAuthThrottle()
        # Isolated, healthy cache — no cross-test global state.
        throttle.cache = LocMemCache("throttle-test-loc", {})
        request = factory.get("/api/v1/auth/login/")

        results = [throttle.allow_request(request, view=None) for _ in range(6)]

        # 5/min: first five allowed, sixth blocked. Fail-open must NOT disable
        # throttling when the cache is healthy.
        assert results[:5] == [True, True, True, True, True]
        assert results[5] is False


class TestFailOpenScopedRateThrottle:
    def test_allows_request_when_cache_raises(self, caplog):
        throttle = FailOpenScopedRateThrottle()
        throttle.cache = Mock()
        throttle.cache.get.side_effect = CacheUnavailable("boom")

        request = factory.get("/api/v1/feedback/")
        with caplog.at_level("WARNING"):
            allowed = throttle.allow_request(request, view=_ScopedView())

        assert allowed is True
        assert "failing open" in caplog.text.lower()


@pytest.mark.django_db
class TestAuthEndpointCacheResilience:
    """End-to-end: the login endpoint must not 500 when the cache is down.

    Without the fail-open throttle these 500 (the original production bug),
    because DRF runs throttle checks in initial() before view dispatch.
    """

    @override_settings(CACHES=RAISING_CACHE)
    def test_login_get_returns_405_not_500_when_cache_down(self, api_client):
        response = api_client.get("/api/v1/auth/login/")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @override_settings(CACHES=RAISING_CACHE)
    def test_login_post_not_500_when_cache_down(self, api_client):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "nobody@example.com", "password": "wrong-password"},
            format="json",
        )
        # Reaches credential validation (and fails it) instead of 500-ing.
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        )

    @override_settings(CACHES=RAISING_CACHE)
    def test_password_change_not_500_when_cache_down(self, authenticated_client):
        client, _user = authenticated_client
        response = client.post(
            "/api/v1/users/me/password/",
            {"old_password": "x", "new_password": "y"},
            format="json",
        )
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
