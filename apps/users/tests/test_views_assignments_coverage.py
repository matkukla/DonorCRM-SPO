"""
Coverage-focused behavioral tests for apps.users.views_assignments.AssignmentsView.

The existing test_m2m_assignments.py covers the happy paths and GET role-filtering.
These tests target the PATCH error/validation/coach branches and the 5+ supervisor
warning that remain uncovered.
"""

import uuid

from rest_framework.test import APIClient

import pytest

from apps.users.tests.factories import (
    AdminUserFactory,
    CoachUserFactory,
    SupervisorUserFactory,
    UserFactory,
)


def _admin_client():
    """Return an APIClient authenticated as an admin user."""
    client = APIClient()
    client.force_authenticate(user=AdminUserFactory())
    return client


@pytest.mark.django_db
class TestAssignmentsPermissions:
    """Only admins may reach the assignments endpoint."""

    def test_missionary_forbidden(self):
        """A non-admin (missionary) is denied access with 403."""
        client = APIClient()
        client.force_authenticate(user=UserFactory())

        response = client.get("/api/v1/users/admin/assignments/")

        assert response.status_code == 403


@pytest.mark.django_db
class TestAssignmentsPatchValidation:
    """PATCH payload validation and per-item error handling."""

    def test_assignments_must_be_a_list(self):
        """A non-list `assignments` value returns 400 with an explanatory detail."""
        client = _admin_client()

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {"assignments": {"not": "a list"}},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["detail"] == "assignments must be a list"

    def test_unknown_missionary_id_recorded_as_error(self):
        """An unknown missionary id produces a per-item error and is not counted."""
        client = _admin_client()
        missing_id = str(uuid.uuid4())

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {"assignments": [{"missionary_id": missing_id, "supervisor_ids": []}]},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["updated"] == 0
        assert len(response.data["errors"]) == 1
        assert response.data["errors"][0]["missionary_id"] == missing_id
        assert "not a missionary" in response.data["errors"][0]["error"].lower()

    def test_non_missionary_target_recorded_as_error(self):
        """Targeting a supervisor (wrong role) as the missionary yields an error."""
        client = _admin_client()
        supervisor = SupervisorUserFactory()

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {"assignments": [{"missionary_id": str(supervisor.id), "supervisor_ids": []}]},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["updated"] == 0
        assert len(response.data["errors"]) == 1

    def test_invalid_supervisor_id_recorded_as_error(self):
        """A supervisor id that does not resolve to a supervisor is rejected per-item."""
        client = _admin_client()
        missionary = UserFactory()
        not_a_supervisor = UserFactory()  # role missionary, not supervisor

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {
                "assignments": [
                    {
                        "missionary_id": str(missionary.id),
                        "supervisor_ids": [str(not_a_supervisor.id)],
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["updated"] == 0
        assert len(response.data["errors"]) == 1
        assert "Supervisor" in response.data["errors"][0]["error"]
        # The invalid assignment must not have been applied.
        missionary.refresh_from_db()
        assert missionary.supervisors.count() == 0

    def test_invalid_coach_id_recorded_as_error(self):
        """A coach id that does not resolve to a coach is rejected per-item."""
        client = _admin_client()
        missionary = UserFactory()
        not_a_coach = UserFactory()

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {
                "assignments": [
                    {
                        "missionary_id": str(missionary.id),
                        "coach_ids": [str(not_a_coach.id)],
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["updated"] == 0
        assert len(response.data["errors"]) == 1
        assert "Coach" in response.data["errors"][0]["error"]
        missionary.refresh_from_db()
        assert missionary.coaches.count() == 0


@pytest.mark.django_db
class TestAssignmentsPatchCoaches:
    """Coach assignment set / additive branches."""

    def test_set_coaches_replaces(self):
        """Non-additive coach assignment replaces the coach set."""
        client = _admin_client()
        missionary = UserFactory()
        coach1 = CoachUserFactory()
        coach2 = CoachUserFactory()
        missionary.coaches.add(coach1)

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {"assignments": [{"missionary_id": str(missionary.id), "coach_ids": [str(coach2.id)]}]},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["updated"] == 1
        missionary.refresh_from_db()
        coach_ids = set(missionary.coaches.values_list("id", flat=True))
        assert coach_ids == {coach2.id}

    def test_additive_coaches_appends(self):
        """Additive coach assignment keeps existing and adds new coaches."""
        client = _admin_client()
        missionary = UserFactory()
        coach1 = CoachUserFactory()
        coach2 = CoachUserFactory()
        missionary.coaches.add(coach1)

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {
                "assignments": [
                    {
                        "missionary_id": str(missionary.id),
                        "coach_ids": [str(coach2.id)],
                        "additive": True,
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        missionary.refresh_from_db()
        coach_ids = set(missionary.coaches.values_list("id", flat=True))
        assert coach_ids == {coach1.id, coach2.id}


@pytest.mark.django_db
class TestAssignmentsSupervisorWarning:
    """The soft warning emitted when a missionary reaches 5+ supervisors."""

    def test_five_or_more_supervisors_emits_warning(self):
        """Assigning 5 supervisors triggers the 5+ warning in the response."""
        client = _admin_client()
        missionary = UserFactory()
        supervisors = [SupervisorUserFactory() for _ in range(5)]

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {
                "assignments": [
                    {
                        "missionary_id": str(missionary.id),
                        "supervisor_ids": [str(s.id) for s in supervisors],
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["updated"] == 1
        assert len(response.data["warnings"]) == 1
        warning = response.data["warnings"][0]
        assert warning["missionary_id"] == str(missionary.id)
        assert "5+" in warning["warning"]

    def test_fewer_than_five_supervisors_no_warning(self):
        """Assigning fewer than 5 supervisors produces no warning."""
        client = _admin_client()
        missionary = UserFactory()
        supervisors = [SupervisorUserFactory() for _ in range(2)]

        response = client.patch(
            "/api/v1/users/admin/assignments/",
            {
                "assignments": [
                    {
                        "missionary_id": str(missionary.id),
                        "supervisor_ids": [str(s.id) for s in supervisors],
                    }
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["updated"] == 1
        assert response.data["warnings"] == []
