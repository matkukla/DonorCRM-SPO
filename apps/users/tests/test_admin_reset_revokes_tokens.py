"""Admin password reset revokes target refresh tokens — security report #13.

Self-service password change blacklisted outstanding refresh tokens, but admin
reset of another user changed the password without revoking that user's tokens
(CWE-613), leaving a stolen token usable after the reset. Admin reset now
blacklists the target's outstanding tokens, matching the self-change path.

Fails if the revocation is reverted (project rule #1).
"""

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.django_db
def test_admin_reset_blacklists_target_refresh_token():
    admin = User.objects.create_user(
        email="admin-reset@example.com",
        password="pw",
        first_name="Ada",
        last_name="Admin",
        role="admin",
    )
    target = User.objects.create_user(
        email="target-reset@example.com",
        password="oldpw",
        first_name="Tom",
        last_name="Target",
        role="missionary",
    )

    # Target has an outstanding refresh token (e.g. from a prior login).
    refresh = RefreshToken.for_user(target)
    outstanding = OutstandingToken.objects.get(token=str(refresh))
    assert not BlacklistedToken.objects.filter(token=outstanding).exists()

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.post(
        f"/api/v1/users/{target.id}/password/",
        {"new_password": "BrandNewPass123!", "new_password_confirm": "BrandNewPass123!"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK

    # The target's outstanding token is now blacklisted.
    assert BlacklistedToken.objects.filter(token=outstanding).exists()
