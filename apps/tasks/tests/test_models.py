"""
Tests for Task model.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tasks.models import Task, TaskPriority, TaskStatus, TaskType
from apps.tasks.tests.factories import (
    CompletedTaskFactory,
    OverdueTaskFactory,
    TaskFactory,
)
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestTaskModel:
    """Tests for Task model methods and properties."""

    def test_task_str(self):
        """Test task string representation."""
        task = TaskFactory(title='Call John')
        assert 'Call John' in str(task)
        assert 'due:' in str(task)

    def test_task_is_overdue_pending(self):
        """Test is_overdue for overdue pending task."""
        task = OverdueTaskFactory(status=TaskStatus.PENDING)
        assert task.is_overdue is True

    def test_task_is_overdue_in_progress(self):
        """Test is_overdue for overdue in-progress task."""
        task = OverdueTaskFactory(status=TaskStatus.IN_PROGRESS)
        assert task.is_overdue is True

    def test_task_not_overdue_future_date(self):
        """Test is_overdue for future due date."""
        task = TaskFactory(due_date=timezone.now().date() + timedelta(days=7))
        assert task.is_overdue is False

    def test_task_not_overdue_completed(self):
        """Test is_overdue for completed task (even if past due)."""
        task = CompletedTaskFactory(due_date=timezone.now().date() - timedelta(days=5))
        assert task.is_overdue is False

    def test_task_not_overdue_cancelled(self):
        """Test is_overdue for cancelled task (even if past due)."""
        task = TaskFactory(
            status=TaskStatus.CANCELLED,
            due_date=timezone.now().date() - timedelta(days=5)
        )
        assert task.is_overdue is False

    def test_mark_complete(self):
        """Test marking a task as complete."""
        user = UserFactory()
        task = TaskFactory(status=TaskStatus.PENDING)

        task.mark_complete(user)

        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.completed_by == user

    def test_mark_cancelled(self):
        """Test marking a task as cancelled."""
        task = TaskFactory(status=TaskStatus.PENDING)

        task.mark_cancelled()

        assert task.status == TaskStatus.CANCELLED

    def test_task_types(self):
        """Test task type choices."""
        assert TaskType.CALL == 'call'
        assert TaskType.EMAIL == 'email'
        assert TaskType.THANK_YOU == 'thank_you'
        assert TaskType.MEETING == 'meeting'
        assert TaskType.FOLLOW_UP == 'follow_up'

    def test_task_priorities(self):
        """Test task priority choices."""
        assert TaskPriority.LOW == 'low'
        assert TaskPriority.MEDIUM == 'medium'
        assert TaskPriority.HIGH == 'high'
        assert TaskPriority.URGENT == 'urgent'
