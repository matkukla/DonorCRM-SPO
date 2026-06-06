"""
Test scaffold for ViewableUsersView — Phase 52 Wave 1.

These tests specify the TARGET behavior for the /api/users/viewable/ endpoint
that will be implemented in Plan 04.

RED state: all tests fail because /api/users/viewable/ does not exist yet (returns 404 or 405).
GREEN state: all tests pass after Plan 04 implements ViewableUsersView.

Test coverage:
  - VIEWAS-12: Viewable users endpoint (admin sees all missionaries, supervisor sees assigned only)
"""

from rest_framework.test import APIClient

import pytest

# --- ROLE ACCESS ---


@pytest.mark.django_db
def test_admin_sees_missionaries_and_supervisors():
    """Admin GET /api/users/viewable/ returns all active missionaries and supervisors."""
    from apps.users.tests.factories import AdminUserFactory, SupervisorUserFactory, UserFactory

    admin = AdminUserFactory()
    missionary1 = UserFactory()
    missionary2 = UserFactory()
    supervisor = SupervisorUserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/users/viewable/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.data]
    assert str(missionary1.id) in ids
    assert str(missionary2.id) in ids
    # Supervisor should appear (admin can view supervisors)
    assert str(supervisor.id) in ids
    # Admin should not appear in their own list
    assert str(admin.id) not in ids


@pytest.mark.django_db
def test_supervisor_sees_assigned_only():
    """Supervisor GET /api/users/viewable/ returns only missionaries in supervised_users M2M."""
    from apps.users.tests.factories import SupervisorUserFactory, UserFactory

    supervisor = SupervisorUserFactory()
    assigned_missionary = UserFactory()
    unassigned_missionary = UserFactory()
    assigned_missionary.supervisors.add(supervisor)

    client = APIClient()
    client.force_authenticate(user=supervisor)
    response = client.get("/api/v1/users/viewable/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.data]
    assert str(assigned_missionary.id) in ids
    assert str(unassigned_missionary.id) not in ids


@pytest.mark.django_db
def test_missionary_gets_403():
    """Missionary GET /api/users/viewable/ returns 403 (not allowed)."""
    from apps.users.tests.factories import UserFactory

    missionary = UserFactory()

    client = APIClient()
    client.force_authenticate(user=missionary)
    response = client.get("/api/v1/users/viewable/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_gets_401():
    """Unauthenticated GET /api/users/viewable/ returns 401."""
    client = APIClient()
    response = client.get("/api/v1/users/viewable/")

    assert response.status_code == 401


# --- FILTERING ---


@pytest.mark.django_db
def test_inactive_missionaries_excluded():
    """Admin GET /api/users/viewable/ does not include inactive missionaries."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    active_missionary = UserFactory(is_active=True)
    inactive_missionary = UserFactory(is_active=False)

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/users/viewable/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.data]
    assert str(active_missionary.id) in ids
    assert str(inactive_missionary.id) not in ids


@pytest.mark.django_db
def test_admin_roles_excluded():
    """Admin GET /api/users/viewable/ excludes other admins but includes supervisors."""
    from apps.users.tests.factories import AdminUserFactory, SupervisorUserFactory, UserFactory

    admin = AdminUserFactory()
    missionary = UserFactory()
    other_admin = AdminUserFactory()
    supervisor = SupervisorUserFactory()

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/users/viewable/")

    assert response.status_code == 200
    ids = [item["id"] for item in response.data]
    assert str(missionary.id) in ids
    assert str(supervisor.id) in ids
    # Other admins should not appear
    assert str(other_admin.id) not in ids
    # Self should not appear
    assert str(admin.id) not in ids


# --- RESPONSE SHAPE ---


@pytest.mark.django_db
def test_response_shape():
    """Response items have only 'id' and 'full_name' keys (no email, role, etc.)."""
    from apps.users.tests.factories import AdminUserFactory, UserFactory

    admin = AdminUserFactory()
    UserFactory()  # at least one missionary

    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/users/viewable/")

    assert response.status_code == 200
    assert len(response.data) > 0
    for item in response.data:
        assert set(item.keys()) == {"id", "full_name"}
