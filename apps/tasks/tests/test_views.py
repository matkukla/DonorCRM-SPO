"""
Tests for Task API views.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.contacts.tests.factories import ContactFactory
from apps.tasks.models import Task, TaskStatus
from apps.tasks.tests.factories import OverdueTaskFactory, TaskFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestTaskListCreateView:
    """Tests for task list and create endpoints."""

    def test_list_tasks_authenticated(self):
        """Test listing tasks for authenticated user."""
        user = UserFactory(role='staff')
        TaskFactory.create_batch(3, owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/tasks/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_list_tasks_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/v1/tasks/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_task(self):
        """Test creating a task."""
        user = UserFactory(role='staff')
        contact = ContactFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            'title': 'Call John',
            'contact': str(contact.id),
            'task_type': 'call',
            'priority': 'high',
            'due_date': str(timezone.now().date() + timedelta(days=3))
        }

        response = client.post('/api/v1/tasks/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Call John'
        assert response.data['status'] == 'pending'

    def test_create_task_without_contact(self):
        """Test creating a task without contact link."""
        user = UserFactory(role='staff')

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            'title': 'General task',
            'task_type': 'other',
            'priority': 'medium',
            'due_date': str(timezone.now().date() + timedelta(days=7))
        }

        response = client.post('/api/v1/tasks/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['contact'] is None

    def test_staff_only_sees_own_tasks(self):
        """Test that staff only sees their own tasks."""
        user1 = UserFactory(role='staff')
        user2 = UserFactory(role='staff')
        TaskFactory.create_batch(2, owner=user1)
        TaskFactory.create_batch(3, owner=user2)

        client = APIClient()
        client.force_authenticate(user=user1)

        response = client.get('/api/v1/tasks/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2


@pytest.mark.django_db
class TestTaskDetailView:
    """Tests for task detail endpoint."""

    def test_get_task_detail(self):
        """Test getting task detail."""
        user = UserFactory(role='staff')
        task = TaskFactory(owner=user, title='Important task')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f'/api/v1/tasks/{task.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Important task'

    def test_update_task(self):
        """Test updating a task."""
        user = UserFactory(role='staff')
        task = TaskFactory(owner=user, priority='medium')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.patch(
            f'/api/v1/tasks/{task.id}/',
            {'priority': 'urgent'}
        )

        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.priority == 'urgent'

    def test_delete_task(self):
        """Test deleting a task."""
        user = UserFactory(role='staff')
        task = TaskFactory(owner=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(f'/api/v1/tasks/{task.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Task.objects.filter(id=task.id).exists()


@pytest.mark.django_db
class TestTaskCompleteView:
    """Tests for task completion endpoint."""

    def test_complete_task(self):
        """Test marking a task as complete."""
        user = UserFactory(role='staff')
        task = TaskFactory(owner=user, status=TaskStatus.PENDING)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'/api/v1/tasks/{task.id}/complete/')

        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_by == user


@pytest.mark.django_db
class TestOverdueTasksView:
    """Tests for overdue tasks endpoint."""

    def test_list_overdue_tasks(self):
        """Test listing overdue tasks."""
        user = UserFactory(role='staff')

        # Create one overdue task
        overdue_task = OverdueTaskFactory(owner=user)

        # Create one future task
        TaskFactory(owner=user, due_date=timezone.now().date() + timedelta(days=7))

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/tasks/overdue/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == str(overdue_task.id)


@pytest.mark.django_db
class TestUpcomingTasksView:
    """Tests for upcoming tasks endpoint."""

    def test_list_upcoming_tasks(self):
        """Test listing upcoming tasks."""
        user = UserFactory(role='staff')

        # Create tasks for today and next few days
        TaskFactory(owner=user, due_date=timezone.now().date())
        TaskFactory(owner=user, due_date=timezone.now().date() + timedelta(days=3))

        # Create one far future task
        TaskFactory(owner=user, due_date=timezone.now().date() + timedelta(days=30))

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/tasks/upcoming/')

        assert response.status_code == status.HTTP_200_OK
        # Should return tasks due within default upcoming window
        assert response.data['count'] >= 2
