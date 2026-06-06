"""
Tests for broadcast task service functions.
"""

from datetime import timedelta

from django.utils import timezone

from rest_framework.exceptions import ValidationError

import pytest

from apps.tasks.broadcast_services import (
    cancel_broadcast,
    create_broadcast,
    resolve_recipients,
    update_broadcast,
)
from apps.tasks.models import BroadcastTask, Task, TaskStatus
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestResolveRecipients:
    """Tests for resolve_recipients function."""

    def test_all_missionaries_includes_supervisors(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        s1 = UserFactory(role="supervisor")

        result = resolve_recipients(admin, "all_missionaries")
        result_ids = {u.id for u in result}
        assert result_ids == {m1.id, m2.id, s1.id}
        assert admin.id not in result_ids  # sender excluded

    def test_all_supervisors_returns_only_supervisors(self):
        admin = UserFactory(role="admin")
        UserFactory(role="missionary")
        s1 = UserFactory(role="supervisor")
        s2 = UserFactory(role="supervisor")

        result = resolve_recipients(admin, "all_supervisors")
        result_ids = {u.id for u in result}
        assert result_ids == {s1.id, s2.id}

    def test_my_team_returns_supervised_users(self):
        sup = UserFactory(role="supervisor")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        UserFactory(role="missionary")  # not supervised

        sup.supervised_users.add(m1, m2)

        result = resolve_recipients(sup, "my_team")
        result_ids = {u.id for u in result}
        assert result_ids == {m1.id, m2.id}

    def test_specific_users_admin(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        m3 = UserFactory(role="missionary")

        result = resolve_recipients(admin, "specific_users", [m1.id, m2.id])
        result_ids = {u.id for u in result}
        assert result_ids == {m1.id, m2.id}
        assert m3.id not in result_ids

    def test_specific_users_supervisor_filters_to_supervised(self):
        sup = UserFactory(role="supervisor")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        m3 = UserFactory(role="missionary")  # not supervised

        sup.supervised_users.add(m1, m2)

        result = resolve_recipients(sup, "specific_users", [m1.id, m2.id, m3.id])
        result_ids = {u.id for u in result}
        assert result_ids == {m1.id, m2.id}
        assert m3.id not in result_ids

    def test_supervisor_cannot_target_all_missionaries(self):
        sup = UserFactory(role="supervisor")

        with pytest.raises(PermissionError):
            resolve_recipients(sup, "all_missionaries")


@pytest.mark.django_db
class TestCreateBroadcast:
    """Tests for create_broadcast function."""

    def test_creates_broadcast_and_copies(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        m3 = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Team update",
            description="Please review",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        assert BroadcastTask.objects.count() == 1
        copies = Task.objects.filter(broadcast=broadcast)
        assert copies.count() == 3

        for copy in copies:
            assert copy.title == "Team update"
            assert copy.status == TaskStatus.PENDING
            assert copy.owner_id in {m1.id, m2.id, m3.id}

    def test_no_recipients_raises_error(self):
        admin = UserFactory(role="admin")

        with pytest.raises(ValidationError, match="No valid recipients"):
            create_broadcast(
                sender=admin,
                title="Empty broadcast",
                description="",
                task_type="other",
                priority="medium",
                due_date=timezone.now().date() + timedelta(days=7),
                target_type="specific_users",
                specific_user_ids=[],
            )

    def test_recipient_ids_stored_as_strings(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Test",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        assert all(isinstance(rid, str) for rid in broadcast.recipient_ids)
        assert str(m1.id) in broadcast.recipient_ids


@pytest.mark.django_db
class TestUpdateBroadcast:
    """Tests for update_broadcast function."""

    def test_cascades_to_incomplete_only(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        # Extra missionaries populate the broadcast recipient pool (side effect)
        UserFactory(role="missionary")
        UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Original",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        # Mark one copy as completed
        completed_copy = Task.objects.filter(broadcast=broadcast, owner=m1).first()
        completed_copy.mark_complete(m1)

        update_broadcast(broadcast, title="Updated")

        # Completed copy still has old title
        completed_copy.refresh_from_db()
        assert completed_copy.title == "Original"

        # Incomplete copies have updated title
        incomplete = Task.objects.filter(
            broadcast=broadcast,
        ).exclude(status=TaskStatus.COMPLETED)
        for copy in incomplete:
            assert copy.title == "Updated"

    def test_updates_broadcast_fields(self):
        admin = UserFactory(role="admin")
        UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Old title",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        new_date = timezone.now().date() + timedelta(days=14)
        update_broadcast(broadcast, title="New title", due_date=new_date)

        broadcast.refresh_from_db()
        assert broadcast.title == "New title"
        assert broadcast.due_date == new_date


@pytest.mark.django_db
class TestCancelBroadcast:
    """Tests for cancel_broadcast function."""

    def test_deletes_incomplete_keeps_completed(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        # Extra missionaries populate the broadcast recipient pool (side effect)
        UserFactory(role="missionary")
        UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="To cancel",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        # Mark one copy as completed
        completed_copy = Task.objects.filter(broadcast=broadcast, owner=m1).first()
        completed_copy.mark_complete(m1)

        cancel_broadcast(broadcast)

        # Only the completed copy remains
        remaining = Task.objects.filter(broadcast=broadcast)
        assert remaining.count() == 1
        assert remaining.first().status == TaskStatus.COMPLETED

        broadcast.refresh_from_db()
        assert broadcast.is_cancelled is True
        assert broadcast.cancelled_at is not None

    def test_already_cancelled_is_idempotent(self):
        admin = UserFactory(role="admin")
        UserFactory(role="missionary")

        broadcast = create_broadcast(
            sender=admin,
            title="Double cancel",
            description="",
            task_type="other",
            priority="medium",
            due_date=timezone.now().date() + timedelta(days=7),
            target_type="all_missionaries",
        )

        cancel_broadcast(broadcast)
        assert broadcast.is_cancelled is True

        # Second cancel should not raise
        cancel_broadcast(broadcast)
        broadcast.refresh_from_db()
        assert broadcast.is_cancelled is True
