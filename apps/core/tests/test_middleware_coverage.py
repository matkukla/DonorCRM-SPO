"""
Coverage-focused behavioral tests for ViewAsMiddleware.

The existing test_middleware.py drives the force_authenticate path. These tests
exercise the production paths the middleware was built for:
  - JWT Bearer resolution (valid / invalid / malformed / unexpected error)
  - Session-auth (request.user) resolution
  - request.view_as_user actually being attached for downstream views

SECURITY-RELEVANT: confirms only admin/supervisor can activate View As and that
a forged/invalid bearer cannot.
"""
from types import SimpleNamespace
from unittest import mock

from rest_framework.test import APIClient

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.tests.factories import AdminUserFactory, SupervisorUserFactory, UserFactory


def _bearer(user):
    """Return a valid Bearer Authorization header value for ``user``."""
    return f"Bearer {AccessToken.for_user(user)}"


@pytest.mark.django_db
class TestViewAsJWTResolution:
    """View As header resolution via a real JWT Bearer token (production path)."""

    def test_admin_jwt_get_passes_through(self):
        """A valid admin JWT + valid target GET is not blocked by the middleware."""
        admin = AdminUserFactory()
        target = UserFactory()

        client = APIClient()
        response = client.get(
            "/api/v1/contacts/",
            HTTP_AUTHORIZATION=_bearer(admin),
            HTTP_X_VIEW_AS_USER_ID=str(target.id),
        )

        # Not 401 (auth resolved via JWT) and not 403 (admin may view a missionary).
        assert response.status_code not in (401, 403)

    def test_missionary_jwt_blocked_by_role(self):
        """A valid missionary JWT cannot activate View As -> 403 role error."""
        missionary = UserFactory()
        target = UserFactory()

        client = APIClient()
        response = client.get(
            "/api/v1/contacts/",
            HTTP_AUTHORIZATION=_bearer(missionary),
            HTTP_X_VIEW_AS_USER_ID=str(target.id),
        )

        assert response.status_code == 403
        assert response.data["detail"] == "You do not have permission to view as this user."

    def test_supervisor_jwt_blocked_for_unassigned(self):
        """A supervisor JWT for an unassigned missionary is rejected with 403."""
        supervisor = SupervisorUserFactory()
        unassigned = UserFactory()

        client = APIClient()
        response = client.get(
            "/api/v1/contacts/",
            HTTP_AUTHORIZATION=_bearer(supervisor),
            HTTP_X_VIEW_AS_USER_ID=str(unassigned.id),
        )

        assert response.status_code == 403
        assert response.data["detail"] == "You do not have permission to view as this user."

    def test_malformed_bearer_token_passes_through_as_401(self):
        """A garbage Bearer token cannot resolve a viewer -> DRF returns 401."""
        target = UserFactory()

        client = APIClient()
        response = client.get(
            "/api/v1/contacts/",
            HTTP_AUTHORIZATION="Bearer not-a-real-jwt-token",
            HTTP_X_VIEW_AS_USER_ID=str(target.id),
        )

        # Middleware logs+falls through to None; DRF auth then 401s the request.
        assert response.status_code == 401

    def test_unexpected_jwt_error_logs_warning_and_returns_none(self):
        """An unexpected JWT parse error is caught, logged as a warning, viewer is None.

        Driven directly against the middleware so the patched get_validated_token
        only affects the middleware's own resolution path (not DRF's later auth).
        """
        from apps.core.middleware import ViewAsMiddleware

        target = UserFactory()
        admin = AdminUserFactory()
        sentinel = object()
        middleware = ViewAsMiddleware(lambda request: sentinel)

        rf_request = SimpleNamespace(
            META={
                "HTTP_X_VIEW_AS_USER_ID": str(target.id),
                "HTTP_AUTHORIZATION": _bearer(admin),
            },
            method="GET",
        )

        with mock.patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.get_validated_token",
            side_effect=ValueError("boom"),
        ):
            with mock.patch("apps.core.middleware.logger.warning") as warn_mock:
                result = middleware(rf_request)

        # Viewer unresolved -> middleware passes through to get_response (sentinel).
        assert result is sentinel
        assert not hasattr(rf_request, "view_as_user")
        warn_mock.assert_called_once()

    def test_invalid_token_logs_info_and_returns_none(self):
        """A bad/expired bearer is caught as the expected case and logged at INFO."""
        from apps.core.middleware import ViewAsMiddleware

        target = UserFactory()
        sentinel = object()
        middleware = ViewAsMiddleware(lambda request: sentinel)

        rf_request = SimpleNamespace(
            META={
                "HTTP_X_VIEW_AS_USER_ID": str(target.id),
                "HTTP_AUTHORIZATION": "Bearer clearly-not-valid",
            },
            method="GET",
        )

        with mock.patch("apps.core.middleware.logger.info") as info_mock:
            result = middleware(rf_request)

        assert result is sentinel
        assert not hasattr(rf_request, "view_as_user")
        info_mock.assert_called_once()


@pytest.mark.django_db
class TestViewAsAttachesTarget:
    """The middleware must set request.view_as_user so downstream views can scope."""

    def test_view_as_user_attached_for_admin(self):
        """A valid admin View As GET attaches request.view_as_user == target."""
        from apps.core.middleware import ViewAsMiddleware

        admin = AdminUserFactory()
        target = UserFactory()

        captured = {}

        def fake_get_response(request):
            captured["view_as_user"] = getattr(request, "view_as_user", None)
            return SimpleNamespace(status_code=200)

        middleware = ViewAsMiddleware(fake_get_response)

        rf_request = SimpleNamespace(
            META={"HTTP_X_VIEW_AS_USER_ID": str(target.id)},
            method="GET",
            _force_auth_user=admin,
            # request.user fallback must not falsely satisfy is_authenticated.
            user=SimpleNamespace(is_authenticated=False),
        )

        middleware(rf_request)

        assert captured["view_as_user"] is not None
        assert captured["view_as_user"].id == target.id

    def test_session_auth_path_resolves_viewer(self):
        """When only request.user is authenticated (session auth), it is used as viewer."""
        from apps.core.middleware import ViewAsMiddleware

        admin = AdminUserFactory()
        target = UserFactory()

        captured = {}

        def fake_get_response(request):
            captured["view_as_user"] = getattr(request, "view_as_user", None)
            return SimpleNamespace(status_code=200)

        middleware = ViewAsMiddleware(fake_get_response)

        rf_request = SimpleNamespace(
            META={"HTTP_X_VIEW_AS_USER_ID": str(target.id)},
            method="GET",
            # No force-auth user; session user is the admin (is_authenticated True).
            _force_auth_user=None,
            user=admin,
        )

        middleware(rf_request)

        assert captured["view_as_user"].id == target.id

    def test_no_header_passes_through_untouched(self):
        """Absent header short-circuits: get_response is called, no view_as_user set."""
        from apps.core.middleware import ViewAsMiddleware

        captured = {}

        def fake_get_response(request):
            captured["called"] = True
            captured["view_as_user"] = getattr(request, "view_as_user", "UNSET")
            return SimpleNamespace(status_code=200)

        middleware = ViewAsMiddleware(fake_get_response)

        rf_request = SimpleNamespace(META={}, method="GET")  # no X-View-As header

        middleware(rf_request)

        assert captured["called"] is True
        assert captured["view_as_user"] == "UNSET"
