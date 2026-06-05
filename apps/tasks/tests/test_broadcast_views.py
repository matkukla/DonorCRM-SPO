"""
Tests for broadcast task API views.
"""
from datetime import timedelta

from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.tasks.broadcast_services import create_broadcast
from apps.tasks.models import BroadcastTask, Task, TaskStatus
from apps.tasks.tests.factories import TaskFactory
from apps.users.tests.factories import UserFactory


def _broadcast_url(pk=None, action=None):
    """Build broadcast API URL."""
    base = "/api/v1/tasks/broadcasts/"
    if pk:
        base += f"{pk}/"
    if action:
        base += f"{action}/"
    return base


def _task_url(pk=None):
    """Build task API URL."""
    base = "/api/v1/tasks/"
    if pk:
        base += f"{pk}/"
    return base


@pytest.mark.django_db
class TestBroadcastListCreate:
    """Tests for broadcast list and create endpoints."""

    def test_admin_create_broadcast(self):
        admin = UserFactory(role="admin")
        UserFactory(role="missionary")
        UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=admin)

        data = {
            "title": "Team update",
            "description": "Please review this.",
            "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
            "target_type": "all_missionaries",
        }

        response = client.post(_broadcast_url(), data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["id"] is not None
        assert response.data["recipient_count"] == 2

    def test_supervisor_create_for_team(self):
        sup = UserFactory(role="supervisor")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        sup.supervised_users.add(m1, m2)

        client = APIClient()
        client.force_authenticate(user=sup)

        data = {
            "title": "Team task",
            "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
            "target_type": "my_team",
        }

        response = client.post(_broadcast_url(), data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["recipient_count"] == 2

    def test_supervisor_cannot_target_all_missionaries(self):
        sup = UserFactory(role="supervisor")
        UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=sup)

        data = {
            "title": "Should fail",
            "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
            "target_type": "all_missionaries",
        }

        response = client.post(_broadcast_url(), data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missionary_cannot_create(self):
        missionary = UserFactory(role="missionary")

        client = APIClient()
        client.force_authenticate(user=missionary)

        data = {
            "title": "Should fail",
            "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
            "target_type": "all_missionaries",
        }

        response = client.post(_broadcast_url(), data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_list_sees_all(self):
        admin = UserFactory(role="admin")
        sup = UserFactory(role="supervisor")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        sup.supervised_users.add(m1)

        # Create one broadcast from admin, one from supervisor
        create_broadcast(
            sender=admin,
            title="Admin broadcast",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )
        create_broadcast(
            sender=sup,
            title="Supervisor broadcast",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="my_team",
        )

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(_broadcast_url())
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 2

    def test_supervisor_list_sees_own_only(self):
        admin = UserFactory(role="admin")
        sup = UserFactory(role="supervisor")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        sup.supervised_users.add(m1)

        create_broadcast(
            sender=admin,
            title="Admin broadcast",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )
        create_broadcast(
            sender=sup,
            title="Sup broadcast",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="my_team",
        )

        client = APIClient()
        client.force_authenticate(user=sup)

        response = client.get(_broadcast_url())
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Sup broadcast"


@pytest.mark.django_db
class TestBroadcastDetail:
    """Tests for broadcast detail endpoint."""

    def test_get_detail_includes_recipient_ids(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Detail test",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(_broadcast_url(pk=broadcast.id))
        assert response.status_code == status.HTTP_200_OK
        assert "recipient_ids" in response.data
        assert str(m1.id) in response.data["recipient_ids"]

    def test_patch_cascades_to_copies(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        m3 = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Before patch",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        # Mark one copy completed
        completed_copy = Task.objects.filter(broadcast=broadcast, owner=m1).first()
        completed_copy.mark_complete(m1)

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.patch(
            _broadcast_url(pk=broadcast.id),
            {"title": "After patch"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Incomplete copies should be updated
        incomplete = Task.objects.filter(
            broadcast=broadcast,
        ).exclude(status=TaskStatus.COMPLETED)
        for copy in incomplete:
            assert copy.title == "After patch"

        # Completed copy should keep old title
        completed_copy.refresh_from_db()
        assert completed_copy.title == "Before patch"


@pytest.mark.django_db
class TestBroadcastCancel:
    """Tests for broadcast cancel endpoint."""

    def test_cancel_removes_incomplete(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        m3 = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="To cancel",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        # Mark one copy completed
        completed_copy = Task.objects.filter(broadcast=broadcast, owner=m1).first()
        completed_copy.mark_complete(m1)

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post(_broadcast_url(pk=broadcast.id, action="cancel"))
        assert response.status_code == status.HTTP_200_OK

        # GET copies: only completed should remain
        copies_response = client.get(_broadcast_url(pk=broadcast.id, action="copies"))
        assert copies_response.status_code == status.HTTP_200_OK
        assert copies_response.data["count"] == 1


@pytest.mark.django_db
class TestBroadcastCopyList:
    """Tests for broadcast copy list endpoint."""

    def test_list_copies(self):
        admin = UserFactory(role="admin")
        UserFactory(role="missionary")
        UserFactory(role="missionary")
        UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Copy list test",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get(_broadcast_url(pk=broadcast.id, action="copies"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

        # Each copy should have owner_name
        for result in response.data["results"]:
            assert "owner_name" in result
            assert result["owner_name"] is not None


@pytest.mark.django_db
class TestMissionaryRestrictions:
    """Tests for missionary restrictions on broadcast task copies."""

    def test_missionary_cannot_edit_broadcast_task(self):
        admin = UserFactory(role="admin")
        missionary = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Cannot edit",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="specific_users",
            specific_user_ids=[missionary.id],
        )

        copy = Task.objects.get(broadcast=broadcast, owner=missionary)

        client = APIClient()
        client.force_authenticate(user=missionary)

        response = client.patch(
            _task_url(pk=copy.id),
            {"title": "Edited title"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missionary_cannot_delete_broadcast_task(self):
        admin = UserFactory(role="admin")
        missionary = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Cannot delete",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="specific_users",
            specific_user_ids=[missionary.id],
        )

        copy = Task.objects.get(broadcast=broadcast, owner=missionary)

        client = APIClient()
        client.force_authenticate(user=missionary)

        response = client.delete(_task_url(pk=copy.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missionary_can_complete_broadcast_task(self):
        admin = UserFactory(role="admin")
        missionary = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Can complete",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="specific_users",
            specific_user_ids=[missionary.id],
        )

        copy = Task.objects.get(broadcast=broadcast, owner=missionary)

        client = APIClient()
        client.force_authenticate(user=missionary)

        response = client.post(f"{_task_url(pk=copy.id)}complete/")
        assert response.status_code == status.HTTP_200_OK

    def test_missionary_can_edit_own_regular_task(self):
        missionary = UserFactory(role="missionary")
        task = TaskFactory(owner=missionary, broadcast=None)

        client = APIClient()
        client.force_authenticate(user=missionary)

        response = client.patch(
            _task_url(pk=task.id),
            {"title": "New title"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.title == "New title"
