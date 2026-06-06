"""
Tests for get_visible_user_ids() permission scoping.

Verifies that:
  - admin sees only own data (returns {admin.id})
  - supervisor sees only own data (returns {sup.id})
  - coach sees own + coached users (returns {coach.id} ∪ coached_user_ids)
  - missionary sees only own data (returns {missionary.id})
  - View As override scopes to target user
"""

import pytest

from apps.users.tests.factories import (
    AdminUserFactory,
    CoachUserFactory,
    SupervisorUserFactory,
    UserFactory,
)

# --- ADMIN ---


def test_admin_sees_only_own_data():
    """Admin defaults to own data, returns {admin.id}."""
    from apps.core.permissions import get_visible_user_ids

    admin = AdminUserFactory.build()
    result = get_visible_user_ids(admin)
    assert result == {admin.id}
    assert result is not None


# --- SUPERVISOR ---


@pytest.mark.django_db
def test_supervisor_sees_only_own_data():
    """Supervisor defaults to own data, returns {sup.id}."""
    from apps.core.permissions import get_visible_user_ids

    sup = SupervisorUserFactory()
    missionary = UserFactory()
    missionary.supervisors.add(sup)
    result = get_visible_user_ids(sup)
    assert result == {sup.id}
    assert result is not None


# --- COACH ---


@pytest.mark.django_db
def test_coach_sees_own_and_coached():
    """Coach role returns {coach.id} union {coached user IDs}."""
    from apps.core.permissions import get_visible_user_ids

    coach = CoachUserFactory()
    coached = UserFactory()
    coached.coaches.add(coach)
    result = get_visible_user_ids(coach)
    assert coach.id in result
    assert coached.id in result
    assert result is not None


# --- MISSIONARY ---


def test_missionary_sees_only_own_data():
    """Missionary role returns {missionary.id}."""
    from apps.core.permissions import get_visible_user_ids

    missionary = UserFactory.build()
    result = get_visible_user_ids(missionary)
    assert result == {missionary.id}
    assert result is not None


# --- VIEW AS OVERRIDE ---


def test_view_as_overrides_scoping():
    """When request.view_as_user is set, returns {view_as_user.id} regardless of viewer role."""
    import types

    from apps.core.permissions import get_visible_user_ids

    admin = AdminUserFactory.build()
    view_as_user = UserFactory.build()

    mock_request = types.SimpleNamespace(view_as_user=view_as_user)
    result = get_visible_user_ids(admin, request=mock_request)
    assert result == {view_as_user.id}
