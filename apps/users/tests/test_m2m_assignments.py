"""
RED tests for Phase 46: Multiple Supervisors per Missionary (M2M).

These tests WILL FAIL until Plan 02 (model migration) and Plan 03 (views) are
implemented. They act as a behavioral contract / Nyquist gate for the phase.

Expected failure mode: AttributeError on `user.supervisors` (M2M field not
yet created — current model has ForeignKey `supervisor` not ManyToManyField
`supervisors`).

Run: pytest apps/users/tests/test_m2m_assignments.py -q
"""
import pytest
from rest_framework.test import APIClient

from apps.users.models import User, UserRole
from apps.users.tests.factories import (
    AdminUserFactory,
    CoachUserFactory,
    SupervisorUserFactory,
    UserFactory,
)


# ---------------------------------------------------------------------------
# Model-level M2M behaviors
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestM2MModelBehaviors:
    """Tests for multi-supervisor M2M assignment at the ORM layer."""

    def test_missionary_can_have_multiple_supervisors(self):
        """A missionary can be assigned to 2+ supervisors simultaneously.

        RED: Fails with AttributeError — `user.supervisors` M2M does not exist
        yet (current model has FK `supervisor`).
        """
        missionary = UserFactory()
        sup1 = SupervisorUserFactory()
        sup2 = SupervisorUserFactory()

        # Plan 02 will add `supervisors` ManyToManyField
        missionary.supervisors.add(sup1)
        missionary.supervisors.add(sup2)

        assigned_ids = set(missionary.supervisors.values_list('id', flat=True))
        assert sup1.id in assigned_ids
        assert sup2.id in assigned_ids
        assert missionary.supervisors.count() == 2

    def test_get_visible_user_ids_returns_missionary_for_both_supervisors(self):
        """get_visible_user_ids() returns missionary's ID for both supervisors.

        When the same missionary is assigned to two supervisors, each supervisor
        independently sees that missionary in their visible set.

        RED: Fails with AttributeError on `user.supervisors` M2M.
        """
        from apps.core.permissions import get_visible_user_ids

        missionary = UserFactory()
        sup1 = SupervisorUserFactory()
        sup2 = SupervisorUserFactory()

        # After Plan 02: M2M assignment from missionary → supervisors
        missionary.supervisors.add(sup1)
        missionary.supervisors.add(sup2)

        # Each supervisor independently sees the missionary
        visible_sup1 = get_visible_user_ids(sup1)
        visible_sup2 = get_visible_user_ids(sup2)

        assert missionary.id in visible_sup1, (
            "Supervisor 1 should see the shared missionary"
        )
        assert missionary.id in visible_sup2, (
            "Supervisor 2 should see the shared missionary"
        )


# ---------------------------------------------------------------------------
# AssignmentsView — M2M API shape (GET and PATCH)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAssignmentsViewM2M:
    """Integration tests for AssignmentsView returning/accepting M2M arrays."""

    def _admin_client(self):
        """Return an APIClient authenticated as an admin user."""
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        return client

    def test_get_returns_supervisor_ids_as_list(self):
        """AssignmentsView GET returns `supervisor_ids` as a list, not scalar.

        After Plan 02/03: response shape for each missionary should be:
            {"supervisor_ids": ["uuid1", "uuid2"], "coach_ids": [...]}
        instead of the current {"supervisor_id": "uuid" | null, "coach_id": ...}.

        RED: Current view returns `supervisor_id` (scalar), not `supervisor_ids`
        (list), so this assertion fails.
        """
        client = self._admin_client()
        missionary = UserFactory()
        sup = SupervisorUserFactory()
        # Plan 02 will provide: missionary.supervisors.add(sup)
        missionary.supervisors.add(sup)

        response = client.get('/api/v1/users/admin/assignments/')

        assert response.status_code == 200
        missionaries_data = response.data['missionaries']
        missionary_entry = next(
            (m for m in missionaries_data if str(m['id']) == str(missionary.id)),
            None,
        )
        assert missionary_entry is not None, "Missionary not in response"

        # Plan 03 changes `supervisor_id` → `supervisor_ids` (list field)
        assert 'supervisor_ids' in missionary_entry, (
            "Expected `supervisor_ids` list field, got scalar `supervisor_id`"
        )
        assert isinstance(missionary_entry['supervisor_ids'], list)
        assert str(sup.id) in missionary_entry['supervisor_ids']

    def test_patch_additive_appends_supervisor_assignments(self):
        """PATCH with additive=True appends supervisors without replacing.

        Starting with sup1 assigned, PATCH additive with sup2 should result in
        both sup1 and sup2 assigned — not just sup2.

        RED: Current PATCH replaces the single FK supervisor_id; additive flag
        and list-based supervisor_ids are not implemented yet.
        """
        client = self._admin_client()
        missionary = UserFactory()
        sup1 = SupervisorUserFactory()
        sup2 = SupervisorUserFactory()

        # Setup: assign sup1 via M2M (Plan 02 provides this)
        missionary.supervisors.add(sup1)

        payload = {
            'assignments': [
                {
                    'missionary_id': str(missionary.id),
                    'supervisor_ids': [str(sup2.id)],
                    'additive': True,
                }
            ]
        }
        response = client.patch(
            '/api/v1/users/admin/assignments/',
            data=payload,
            format='json',
        )

        assert response.status_code == 200
        missionary.refresh_from_db()

        # Both should remain after additive patch
        assigned_ids = set(missionary.supervisors.values_list('id', flat=True))
        assert sup1.id in assigned_ids, "Additive patch should not remove sup1"
        assert sup2.id in assigned_ids, "Additive patch should add sup2"

    def test_patch_non_additive_replaces_supervisor_assignments(self):
        """PATCH with additive=False (default) fully replaces supervisor list.

        Starting with sup1 and sup2, PATCH non-additive with only sup3 should
        result in only sup3 assigned.

        RED: Current PATCH uses FK, not M2M; supervisor_ids list not accepted.
        """
        client = self._admin_client()
        missionary = UserFactory()
        sup1 = SupervisorUserFactory()
        sup2 = SupervisorUserFactory()
        sup3 = SupervisorUserFactory()

        # Setup: assign sup1 and sup2 via M2M (Plan 02)
        missionary.supervisors.add(sup1, sup2)

        payload = {
            'assignments': [
                {
                    'missionary_id': str(missionary.id),
                    'supervisor_ids': [str(sup3.id)],
                    # additive defaults to False — full replacement
                }
            ]
        }
        response = client.patch(
            '/api/v1/users/admin/assignments/',
            data=payload,
            format='json',
        )

        assert response.status_code == 200
        missionary.refresh_from_db()

        assigned_ids = set(missionary.supervisors.values_list('id', flat=True))
        assert sup3.id in assigned_ids, "sup3 should be assigned after replacement"
        assert sup1.id not in assigned_ids, "sup1 should be removed on non-additive"
        assert sup2.id not in assigned_ids, "sup2 should be removed on non-additive"


# ---------------------------------------------------------------------------
# Auto-unassign on role change
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAutoUnassignOnRoleChange:
    """Test that changing a supervisor's role clears their M2M assignments."""

    def test_supervised_users_cleared_when_supervisor_becomes_missionary(self):
        """When supervisor's role changes to missionary, supervised_users M2M is cleared.

        The serializer/signal in Plan 03 should handle this automatically.

        RED: No M2M clear-on-role-change logic exists yet; `supervisors` M2M
        field itself is not yet created.
        """
        missionary1 = UserFactory()
        missionary2 = UserFactory()
        sup = SupervisorUserFactory()

        # Assign two missionaries to this supervisor (Plan 02 M2M)
        missionary1.supervisors.add(sup)
        missionary2.supervisors.add(sup)

        assert sup.supervised_users.count() == 2  # noqa: E501 (Plan 02 reverses FK→M2M reverse relation)

        # Change supervisor's role to missionary — Plan 03 should auto-clear
        sup.role = UserRole.MISSIONARY
        sup.save()

        # After role change, no missionaries should be linked to former supervisor
        assert sup.supervised_users.count() == 0, (
            "Changing role away from supervisor should auto-clear supervised_users"
        )


# ---------------------------------------------------------------------------
# Migration preservation (integration / manual test)
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "Migration test: run `pytest --migrations` to verify FK→M2M preservation. "
        "Skipping in unit suite — requires special migration test setup."
    )
)
def test_migration_preserves_existing_fk_supervisor_assignment():
    """Data migration copies FK supervisor_id into supervisors M2M join table.

    A missionary who had `supervisor_id = X` on the old FK schema should appear
    in `missionary.supervisors.all()` after the Plan 02 migration runs.

    This test requires running against the full migration history:
        pytest apps/users/tests/test_m2m_assignments.py::test_migration_preserves_existing_fk_supervisor_assignment --migrations
    """
    # Verify post-migration state — illustrative, not runnable in unit suite
    pass  # pragma: no cover
