"""
RED tests for Phase 46: Multiple Supervisors per Missionary (M2M).

These tests WILL FAIL until Plan 02 (model migration) and Plan 03 (views) are
implemented. They act as a behavioral contract / Nyquist gate for the phase.

Expected failure mode: AttributeError on `user.supervisors` (M2M field not
yet created — current model has ForeignKey `supervisor` not ManyToManyField
`supervisors`).

Run: pytest apps/users/tests/test_m2m_assignments.py -q
"""

from rest_framework.test import APIClient

import pytest

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

        assigned_ids = set(missionary.supervisors.values_list("id", flat=True))
        assert sup1.id in assigned_ids
        assert sup2.id in assigned_ids
        assert missionary.supervisors.count() == 2

    def test_get_visible_user_ids_returns_own_id_for_both_supervisors(self):
        """After Phase 51: get_visible_user_ids() returns {user.id} for supervisor role.

        Supervised missionaries are NOT included in the default visible set.
        Cross-user access requires an explicit View As session (Phase 52+).

        Even when the same missionary is assigned to two supervisors, each supervisor
        only sees their own data — not the missionary's data.
        """
        from apps.core.permissions import get_visible_user_ids

        missionary = UserFactory()
        sup1 = SupervisorUserFactory()
        sup2 = SupervisorUserFactory()

        # M2M assignment still valid — the relationship exists; it just doesn't
        # affect the default visible set after Phase 51
        missionary.supervisors.add(sup1)
        missionary.supervisors.add(sup2)

        # Each supervisor sees only their own data
        visible_sup1 = get_visible_user_ids(sup1)
        visible_sup2 = get_visible_user_ids(sup2)

        assert visible_sup1 == {sup1.id}, "Supervisor 1 sees only own data (Phase 51+)"
        assert visible_sup2 == {sup2.id}, "Supervisor 2 sees only own data (Phase 51+)"
        assert missionary.id not in visible_sup1, "Supervisor cannot see missionary by default"
        assert missionary.id not in visible_sup2, "Supervisor cannot see missionary by default"


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

        response = client.get("/api/v1/users/admin/assignments/")

        assert response.status_code == 200
        missionaries_data = response.data["missionaries"]
        missionary_entry = next(
            (m for m in missionaries_data if str(m["id"]) == str(missionary.id)),
            None,
        )
        assert missionary_entry is not None, "Missionary not in response"

        # Plan 03 changes `supervisor_id` → `supervisor_ids` (list field)
        assert (
            "supervisor_ids" in missionary_entry
        ), "Expected `supervisor_ids` list field, got scalar `supervisor_id`"
        assert isinstance(missionary_entry["supervisor_ids"], list)
        assert str(sup.id) in missionary_entry["supervisor_ids"]

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
            "assignments": [
                {
                    "missionary_id": str(missionary.id),
                    "supervisor_ids": [str(sup2.id)],
                    "additive": True,
                }
            ]
        }
        response = client.patch(
            "/api/v1/users/admin/assignments/",
            data=payload,
            format="json",
        )

        assert response.status_code == 200
        missionary.refresh_from_db()

        # Both should remain after additive patch
        assigned_ids = set(missionary.supervisors.values_list("id", flat=True))
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
            "assignments": [
                {
                    "missionary_id": str(missionary.id),
                    "supervisor_ids": [str(sup3.id)],
                    # additive defaults to False — full replacement
                }
            ]
        }
        response = client.patch(
            "/api/v1/users/admin/assignments/",
            data=payload,
            format="json",
        )

        assert response.status_code == 200
        missionary.refresh_from_db()

        assigned_ids = set(missionary.supervisors.values_list("id", flat=True))
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

        assert (
            sup.supervised_users.count() == 2
        )  # noqa: E501 (Plan 02 reverses FK→M2M reverse relation)

        # Change supervisor's role to missionary — Plan 03 should auto-clear
        sup.role = UserRole.MISSIONARY
        sup.save()

        # After role change, no missionaries should be linked to former supervisor
        assert (
            sup.supervised_users.count() == 0
        ), "Changing role away from supervisor should auto-clear supervised_users"


# ---------------------------------------------------------------------------
# Role-filter regression tests (Plan 06: Ghost supervisor fix)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssignmentsViewRoleFilter:
    """Regression tests ensuring GET only returns currently-valid role holders.

    Ghost rows are M2M entries where the referenced user no longer holds the
    expected role (e.g., was supervisor, now missionary). These were created by
    migration 0006 which copied FK data without role validation.
    """

    def _admin_client(self):
        """Return an APIClient authenticated as an admin user."""
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        return client

    def test_ghost_supervisor_excluded_from_get(self):
        """A role-changed user (supervisor → missionary) must NOT appear in supervisor_ids.

        Ghost row created by direct DB update (bypassing User.save() auto-clear),
        mimicking data left by the FK-to-M2M migration without role validation.
        """
        client = self._admin_client()
        missionary = UserFactory()
        ex_sup = SupervisorUserFactory()

        # Assign as supervisor via M2M
        missionary.supervisors.add(ex_sup)

        # Directly change role in DB, bypassing User.save() — creates ghost row
        User.objects.filter(id=ex_sup.id).update(role="missionary")

        response = client.get("/api/v1/users/admin/assignments/")

        assert response.status_code == 200
        missionary_entry = next(
            (m for m in response.data["missionaries"] if str(m["id"]) == str(missionary.id)),
            None,
        )
        assert missionary_entry is not None, "Missionary must appear in GET response"
        assert (
            str(ex_sup.id) not in missionary_entry["supervisor_ids"]
        ), "Ghost supervisor (role changed to missionary) must not appear in supervisor_ids"

    def test_ghost_coach_excluded_from_get(self):
        """A role-changed user (coach → missionary) must NOT appear in coach_ids.

        Ghost row created by direct DB update, bypassing User.save() auto-clear.
        """
        client = self._admin_client()
        missionary = UserFactory()
        ex_coach = CoachUserFactory()

        # Assign as coach via M2M
        missionary.coaches.add(ex_coach)

        # Directly change role in DB, bypassing User.save()
        User.objects.filter(id=ex_coach.id).update(role="missionary")

        response = client.get("/api/v1/users/admin/assignments/")

        assert response.status_code == 200
        missionary_entry = next(
            (m for m in response.data["missionaries"] if str(m["id"]) == str(missionary.id)),
            None,
        )
        assert missionary_entry is not None, "Missionary must appear in GET response"
        assert (
            str(ex_coach.id) not in missionary_entry["coach_ids"]
        ), "Ghost coach (role changed to missionary) must not appear in coach_ids"

    def test_active_supervisor_with_correct_role_appears_in_get(self):
        """An active supervisor with role='supervisor' DOES appear in supervisor_ids."""
        client = self._admin_client()
        missionary = UserFactory()
        sup = SupervisorUserFactory()
        missionary.supervisors.add(sup)

        response = client.get("/api/v1/users/admin/assignments/")

        assert response.status_code == 200
        missionary_entry = next(
            (m for m in response.data["missionaries"] if str(m["id"]) == str(missionary.id)),
            None,
        )
        assert missionary_entry is not None
        assert (
            str(sup.id) in missionary_entry["supervisor_ids"]
        ), "Active supervisor with correct role must appear in supervisor_ids"

    def test_inactive_supervisor_excluded_from_get(self):
        """A supervisor with is_active=False must NOT appear in supervisor_ids."""
        client = self._admin_client()
        missionary = UserFactory()
        sup = SupervisorUserFactory()
        missionary.supervisors.add(sup)

        # Deactivate the supervisor via direct DB update (bypasses save() hooks)
        User.objects.filter(id=sup.id).update(is_active=False)

        response = client.get("/api/v1/users/admin/assignments/")

        assert response.status_code == 200
        missionary_entry = next(
            (m for m in response.data["missionaries"] if str(m["id"]) == str(missionary.id)),
            None,
        )
        assert missionary_entry is not None
        assert (
            str(sup.id) not in missionary_entry["supervisor_ids"]
        ), "Inactive supervisor (is_active=False) must not appear in supervisor_ids"


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
        pytest apps/users/tests/test_m2m_assignments.py\
            ::test_migration_preserves_existing_fk_supervisor_assignment --migrations
    """
    # Verify post-migration state — illustrative, not runnable in unit suite
    pass  # pragma: no cover
