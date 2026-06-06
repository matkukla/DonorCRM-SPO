"""
URL patterns for authentication endpoints.
"""

from django.urls import path

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.throttling import FailOpenSimpleRateThrottle
from apps.users.views_auth import LogoutView


class _AuthBurstThrottle(FailOpenSimpleRateThrottle):
    """Per-IP burst limit on auth endpoints (rate from THROTTLE_RATES['auth'])."""

    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class _AuthHourThrottle(FailOpenSimpleRateThrottle):
    """Per-IP hourly cap layered on top of the burst throttle to slow
    credential stuffing across short pauses (rate from
    THROTTLE_RATES['auth_hour'])."""

    scope = "auth_hour"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login view with two-tier rate limiting (burst + hourly).

    django-axes provides account-lockout (post-credential-check). The
    throttles below are pre-credential-check — they protect against
    enumeration and slow brute-force from a single source.
    """

    throttle_classes = [_AuthBurstThrottle, _AuthHourThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    """Token refresh with the same two-tier rate limiting as login."""

    throttle_classes = [_AuthBurstThrottle, _AuthHourThrottle]


app_name = "auth"

urlpatterns = [
    path("login/", ThrottledTokenObtainPairView.as_view(), name="login"),
    path("refresh/", ThrottledTokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
