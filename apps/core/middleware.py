import logging

from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from apps.users.models import User

logger = logging.getLogger(__name__)


class ViewAsMiddleware:
    """
    Validates X-View-As-User-Id header and enforces View As read-only mode.

    Behavior:
    - Header absent: passes through unchanged
    - Header present, user unauthenticated: passes through (DRF returns 401)
    - Header present, user not admin/supervisor: 403
    - Header present, target not found/wrong role/inactive: 403
    - Header present, supervisor + non-assigned target: 403
    - Valid header + mutating method (POST/PUT/PATCH/DELETE): 403
    - Valid header + GET: passes through with request.view_as_user set

    Authentication note: DRF JWT auth runs inside APIView.dispatch(), not during
    middleware. This middleware resolves the viewer from JWT (production) or from
    DRF's _force_auth_user test hook, falling back to the session-based
    request.user set by Django's AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header_value = request.META.get("HTTP_X_VIEW_AS_USER_ID")

        if not header_value:
            return self.get_response(request)

        viewer = self._resolve_viewer(request)

        # If we cannot resolve a viewer, pass through — DRF will return 401.
        if viewer is None:
            return self.get_response(request)

        error = self._validate_and_attach(request, header_value, viewer)
        if error:
            return self._json_403(error)

        # Mutation guard runs AFTER validation — only if header is legitimate
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return self._json_403("Mutations are not allowed in View As mode.")

        return self.get_response(request)

    def _json_403(self, detail):
        """Return a rendered 403 response compatible with both DRF and plain Django."""
        response = Response({"detail": detail}, status=403)
        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = "application/json"
        response.renderer_context = {}
        response.render()
        return response

    def _resolve_viewer(self, request):
        """Return the authenticated User for this request, or None.

        Checks three sources in order:
        1. DRF's _force_auth_user (set by APIClient.force_authenticate in tests)
        2. Django's request.user (set by AuthenticationMiddleware for session auth)
        3. JWT Bearer token in the Authorization header (production path)
        """
        # Test path: DRF force_authenticate sets _force_auth_user on the raw request.
        force_user = getattr(request, "_force_auth_user", None)
        if force_user is not None and getattr(force_user, "is_authenticated", False):
            return force_user

        # Session auth path (Django admin, session-based clients).
        if hasattr(request, "user") and request.user.is_authenticated:
            return request.user

        # JWT path: parse the Authorization header directly.
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[len("Bearer ") :].encode()
            try:
                from rest_framework.exceptions import AuthenticationFailed as DRFAuthFailed

                from rest_framework_simplejwt.authentication import JWTAuthentication
                from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(raw_token)
                user = jwt_auth.get_user(validated_token)
                if user and user.is_authenticated:
                    return user
            except (InvalidToken, TokenError, DRFAuthFailed) as exc:
                # Expected: bad/expired/blacklisted token. Log at INFO without
                # the token value. Falls through to None — DRF will return 401.
                logger.info("View-As: rejecting bad bearer token (%s)", exc.__class__.__name__)
            except Exception:
                # Unexpected: log a warning so it surfaces in Sentry. Still
                # falls through to None to avoid leaking internal state.
                logger.warning("View-As: unexpected JWT parse error", exc_info=True)

        return None

    def _validate_and_attach(self, request, target_id_str, viewer):
        """Validate the header value and set request.view_as_user on success.

        Returns error string on failure, None on success.
        """
        if viewer.role not in ("admin", "supervisor"):
            return "You do not have permission to view as this user."

        try:
            target = User.objects.get(
                pk=target_id_str, role__in=["missionary", "supervisor"], is_active=True
            )
        except (User.DoesNotExist, ValueError):
            return "Invalid View As target."

        # Supervisors can only view their assigned missionaries (not other supervisors)
        if viewer.role == "supervisor":
            if (
                target.role != "missionary"
                or not viewer.supervised_users.filter(pk=target.pk).exists()
            ):
                return "You do not have permission to view as this user."

        request.view_as_user = target
        from apps.core.audit import audit_event

        audit_event(
            "authz.view_as.activated",
            actor_id=viewer.id,
            target_id=target.id,
            actor_role=viewer.role,
        )
        return None
