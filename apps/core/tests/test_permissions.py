"""
Test scaffold for get_visible_user_ids() — Phase 51 Wave 0.

These tests specify the TARGET behavior after Phase 51 is fully implemented.

RED/GREEN state per test (before Plan 02 changes the implementation):
  - test_admin_sees_only_own_data     RED   — current function returns None, test asserts {admin.id}
  - test_supervisor_sees_only_own_data RED  — current function returns {own+supervised}, test asserts {sup.id}
  - test_finance_sees_all             GREEN — unchanged behavior (None)
  - test_read_only_sees_all           GREEN — unchanged behavior (None)
  - test_coach_sees_own_and_coached   GREEN — unchanged behavior ({own+coached})
  - test_missionary_sees_only_own_data GREEN — unchanged behavior ({own})

After Plan 02 all 6 tests must pass.
"""
import pytest

from apps.users.tests.factories import (
    AdminUserFactory,
    CoachUserFactory,
    FinanceUserFactory,
    ReadOnlyUserFactory,
    SupervisorUserFactory,
    UserFactory,
)


# --- ADMIN ---

def test_admin_sees_only_own_data():
    """After Phase 51: admin defaults to own data, returns {admin.id} not None."""
    from apps.core.permissions import get_visible_user_ids
    admin = AdminUserFactory.build()
    result = get_visible_user_ids(admin)
    assert result == {admin.id}
    assert result is not None  # Explicit: admin no longer returns None


# --- SUPERVISOR ---

@pytest.mark.django_db
def test_supervisor_sees_only_own_data():
    """After Phase 51: supervisor defaults to own data, returns {sup.id} not {own+supervised}.

    A missionary is assigned to the supervisor so the current code (pre-Plan 02) returns
    {sup.id, missionary.id}, causing this test to fail in RED state. After Plan 02, the
    supervisor branch returns {user.id} directly without querying supervised_users.
    """
    from apps.core.permissions import get_visible_user_ids
    sup = SupervisorUserFactory()
    missionary = UserFactory()
    missionary.supervisors.add(sup)  # assign missionary to supervisor
    result = get_visible_user_ids(sup)
    assert result == {sup.id}  # only own data — NOT the missionary's id
    assert result is not None


# --- FINANCE ---

@pytest.mark.django_db
def test_finance_sees_all():
    """Finance role is unchanged: returns None (all-access sentinel)."""
    from apps.core.permissions import get_visible_user_ids
    finance = FinanceUserFactory()
    result = get_visible_user_ids(finance)
    assert result is None


# --- READ ONLY ---

@pytest.mark.django_db
def test_read_only_sees_all():
    """Read-only role is unchanged: returns None (all-access sentinel)."""
    from apps.core.permissions import get_visible_user_ids
    ro = ReadOnlyUserFactory()
    result = get_visible_user_ids(ro)
    assert result is None


# --- COACH ---

@pytest.mark.django_db
def test_coach_sees_own_and_coached():
    """Coach role is unchanged: returns {coach.id} union {coached user IDs}."""
    from apps.core.permissions import get_visible_user_ids
    coach = CoachUserFactory()
    coached = UserFactory()
    coached.coaches.add(coach)  # coaches is the M2M on User; coached.coaches -> coaches assigned to this user
    result = get_visible_user_ids(coach)
    assert coach.id in result
    assert coached.id in result
    assert result is not None


# --- MISSIONARY ---

def test_missionary_sees_only_own_data():
    """Missionary role is unchanged: returns {missionary.id}."""
    from apps.core.permissions import get_visible_user_ids
    missionary = UserFactory.build()
    result = get_visible_user_ids(missionary)
    assert result == {missionary.id}
    assert result is not None
