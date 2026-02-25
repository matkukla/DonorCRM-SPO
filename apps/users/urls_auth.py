"""
URL patterns for authentication endpoints.
"""
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.users.views_auth import LogoutView


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login view with rate limiting to prevent brute-force attacks."""
    throttle_scope = 'auth'


class ThrottledTokenRefreshView(TokenRefreshView):
    """Token refresh view with rate limiting."""
    throttle_scope = 'auth'


app_name = 'auth'

urlpatterns = [
    path('login/', ThrottledTokenObtainPairView.as_view(), name='login'),
    path('refresh/', ThrottledTokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
