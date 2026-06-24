"""Offboarding control: deactivating a user revokes their refresh tokens.

When an admin deactivates (soft-deletes) a user, the user's outstanding
refresh tokens must be blacklisted so a departed/compromised account cannot
mint new access tokens via /auth/refresh/ (CWE-613). This mirrors the
password-change and admin-reset paths, which already revoke tokens.

Without the fix the refresh token survives deactivation and the refresh
endpoint keeps issuing access tokens until the refresh itself expires (7 days).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def deactivation_setup(db):
    admin = User.objects.create_user(email="admin-deact@example.com", password="pw", role="admin")
    target = User.objects.create_user(
        email="target-deact@example.com", password="pw", role="missionary"
    )
    refresh = RefreshToken.for_user(target)  # records an OutstandingToken
    return {"admin": admin, "target": target, "refresh": refresh}


@pytest.mark.django_db
class TestDeactivationRevokesTokens:
    def test_deactivate_blacklists_outstanding_tokens(self, deactivation_setup):
        target = deactivation_setup["target"]
        assert OutstandingToken.objects.filter(user=target).exists()
        assert not BlacklistedToken.objects.filter(token__user=target).exists()

        client = APIClient()
        client.force_authenticate(user=deactivation_setup["admin"])
        resp = client.delete(f"/api/v1/users/{target.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        target.refresh_from_db()
        assert target.is_active is False
        # Every outstanding refresh token for the deactivated user is revoked.
        assert BlacklistedToken.objects.filter(token__user=target).exists()

    def test_deactivated_user_cannot_refresh(self, deactivation_setup):
        target = deactivation_setup["target"]
        refresh = deactivation_setup["refresh"]

        admin_client = APIClient()
        admin_client.force_authenticate(user=deactivation_setup["admin"])
        admin_client.delete(f"/api/v1/users/{target.id}/")

        # The blacklisted refresh token must be rejected by the refresh endpoint.
        resp = APIClient().post("/api/v1/auth/refresh/", {"refresh": str(refresh)}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
