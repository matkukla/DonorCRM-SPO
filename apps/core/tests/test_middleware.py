"""
Test scaffold for ViewAsMiddleware — Phase 52 Wave 1.

These tests specify the TARGET behavior for the middleware that will be
implemented in Plan 02.

RED state: all tests fail because apps/core/middleware.py does not exist yet.
GREEN state: all tests pass after Plan 02 implements ViewAsMiddleware.

Test coverage:
  - VIEWAS-07: Mutation blocking (POST/PUT/PATCH/DELETE blocked when header present)
  - VIEWAS-08: Permission validation (only admin/supervisor can use header; target must be valid)
"""

from rest_framework.test import APIClient

import pytest

# --- MUTATION BLOCKING (VIEWAS-07) ---


@pytest.mark.django_db
def test_mutation_blocked_post():
    """POST with X-View-As-User-Id header returns 403 with mutation error."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    target = UserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.post(
        "/api/v1/contacts/",
        data={"name": "Test"},
        HTTP_X_VIEW_AS_USER_ID=str(target.id),
    )
    assert response.status_code == 403
    assert response.data["detail"] == "Mutations are not allowed in View As mode."


@pytest.mark.django_db
def test_mutation_blocked_put():
    """PUT with X-View-As-User-Id header returns 403 with mutation error."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    target = UserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.put(
        "/api/v1/contacts/",
        data={"name": "Test"},
        HTTP_X_VIEW_AS_USER_ID=str(target.id),
    )
    assert response.status_code == 403
    assert response.data["detail"] == "Mutations are not allowed in View As mode."


@pytest.mark.django_db
def test_mutation_blocked_patch():
    """PATCH with X-View-As-User-Id header returns 403 with mutation error."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    target = UserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.patch(
        "/api/v1/contacts/",
        data={"name": "Test"},
        HTTP_X_VIEW_AS_USER_ID=str(target.id),
    )
    assert response.status_code == 403
    assert response.data["detail"] == "Mutations are not allowed in View As mode."


@pytest.mark.django_db
def test_mutation_blocked_delete():
    """DELETE with X-View-As-User-Id header returns 403 with mutation error."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    target = UserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.delete(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=str(target.id),
    )
    assert response.status_code == 403
    assert response.data["detail"] == "Mutations are not allowed in View As mode."


# --- GET ALLOWED IN VIEW AS ---


@pytest.mark.django_db
def test_get_allowed_in_view_as():
    """GET with valid View As header is not blocked by middleware (passes through to DRF)."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    target = UserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=str(target.id),
    )
    # Should not be 403 from middleware (may be 200, 404, etc. from the view)
    assert response.status_code != 403


# --- PERMISSION VALIDATION (VIEWAS-08) ---


@pytest.mark.django_db
def test_unauthorized_role_blocked():
    """Missionary sending View As header returns 403 with role error."""
    from apps.users.tests.factories import UserFactory

    missionary = UserFactory()
    target = UserFactory()

    client = APIClient()
    client.force_authenticate(user=missionary)
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=str(target.id),
    )
    assert response.status_code == 403
    assert response.data["detail"] == "You do not have permission to view as this user."


@pytest.mark.django_db
def test_admin_can_view_as_any_missionary():
    """Admin with valid missionary target header: request passes through (not 403)."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    target = UserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=str(target.id),
    )
    # Middleware should not block this — admin can view any missionary
    assert response.status_code != 403


@pytest.mark.django_db
def test_supervisor_blocked_for_unassigned():
    """Supervisor sending header for non-assigned missionary returns 403."""
    from apps.users.tests.factories import SupervisorUserFactory, UserFactory

    supervisor = SupervisorUserFactory()
    unassigned_missionary = UserFactory()  # NOT added to supervisor's supervised_users

    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=str(unassigned_missionary.id),
    )
    assert response.status_code == 403
    assert response.data["detail"] == "You do not have permission to view as this user."


@pytest.mark.django_db
def test_supervisor_allowed_for_assigned():
    """Supervisor sending header for assigned missionary: request passes through (not 403)."""
    from apps.users.tests.factories import SupervisorUserFactory, UserFactory

    supervisor = SupervisorUserFactory()
    assigned_missionary = UserFactory()
    assigned_missionary.supervisors.add(supervisor)

    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=str(assigned_missionary.id),
    )
    # Middleware should not block — supervisor can view assigned missionary
    assert response.status_code != 403


@pytest.mark.django_db
def test_invalid_user_id_returns_403():
    """Non-existent UUID in header returns 403 with invalid target error."""
    import uuid

    from apps.users.tests.factories import AdminUserFactory

    admin = AdminUserFactory()
    non_existent_id = str(uuid.uuid4())

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=non_existent_id,
    )
    assert response.status_code == 403
    assert response.data["detail"] == "Invalid View As target."


@pytest.mark.django_db
def test_inactive_target_returns_403():
    """Inactive missionary UUID in header returns 403 with invalid target error."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    inactive_target = UserFactory(is_active=False)

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=str(inactive_target.id),
    )
    assert response.status_code == 403
    assert response.data["detail"] == "Invalid View As target."


@pytest.mark.django_db
def test_unauthenticated_with_header():
    """Unauthenticated request with View As header passes through middleware (DRF returns 401)."""
    import uuid

    some_id = str(uuid.uuid4())

    client = APIClient()
    # No force_authenticate — unauthenticated request
    response = client.get(
        "/api/v1/contacts/",
        HTTP_X_VIEW_AS_USER_ID=some_id,
    )
    # Middleware should pass through (not 403); DRF authentication returns 401
    assert response.status_code == 401
