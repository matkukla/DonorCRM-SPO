"""
Behavioral coverage tests for the Task CSV export view.

StreamingHttpResponse generators silently swallow exceptions, so a broken
export can still return 200 with a header row but NO data rows. These tests
parse the streamed body and assert the header AND at least one correct data
row, which catches that class of bug.
"""

import csv
import io
from datetime import date

from django.utils import timezone

from rest_framework.test import APIClient

import pytest

from apps.contacts.tests.factories import ContactFactory
from apps.tasks.models import Task, TaskPriority, TaskStatus, TaskType
from apps.users.tests.factories import UserFactory

EXPORT_URL = "/api/v1/tasks/export/csv/"


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _parse_csv(response):
    body = b"".join(response.streaming_content).decode("utf-8")
    return list(csv.reader(io.StringIO(body)))


@pytest.fixture
def missionary():
    return UserFactory(role="missionary", email="task-export-owner@test.com")


@pytest.mark.django_db
class TestTaskExportCSV:
    def test_export_header_and_data_row(self, missionary):
        contact = ContactFactory(owner=missionary, first_name="Tara", last_name="Contact")
        Task.objects.create(
            owner=missionary,
            contact=contact,
            title="Follow up call",
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            task_type=TaskType.CALL,
            due_date=date(2026, 7, 4),
        )
        response = _client(missionary).get(EXPORT_URL)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert response["Content-Disposition"].startswith("attachment; filename=")
        assert "tasks_" in response["Content-Disposition"]

        rows = _parse_csv(response)
        assert rows[0] == [
            "Title",
            "Contact",
            "Status",
            "Priority",
            "Type",
            "Due Date",
            "Created At",
        ]
        assert len(rows) == 2
        data = rows[1]
        assert data[0] == "Follow up call"
        assert data[1] == "Tara Contact"
        assert data[2] == TaskStatus.PENDING
        assert data[3] == TaskPriority.HIGH
        assert data[4] == TaskType.CALL
        assert data[5] == "2026-07-04"
        # Created At is a non-empty ISO timestamp.
        assert data[6] != ""
        assert "T" in data[6]

    def test_export_task_without_contact(self, missionary):
        # Task.due_date is NOT NULL on the model, so it always has a value.
        Task.objects.create(
            owner=missionary,
            contact=None,
            title="No contact task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.LOW,
            task_type=TaskType.OTHER,
            due_date=date(2026, 11, 15),
        )
        response = _client(missionary).get(EXPORT_URL)
        rows = _parse_csv(response)
        assert len(rows) == 2
        data = rows[1]
        assert data[0] == "No contact task"
        # Missing contact renders as empty string, not a crash.
        assert data[1] == ""
        assert data[5] == "2026-11-15"

    def test_export_only_includes_owned_tasks(self, missionary):
        own_contact = ContactFactory(owner=missionary, first_name="Own", last_name="One")
        Task.objects.create(
            owner=missionary,
            contact=own_contact,
            title="My task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.OTHER,
            due_date=date(2026, 8, 1),
        )
        other = UserFactory(role="missionary", email="other-task@test.com")
        other_contact = ContactFactory(owner=other)
        Task.objects.create(
            owner=other,
            contact=other_contact,
            title="Their task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.OTHER,
            due_date=date(2026, 8, 1),
        )
        response = _client(missionary).get(EXPORT_URL)
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][0] == "My task"

    def test_export_applies_status_filter(self, missionary):
        contact = ContactFactory(owner=missionary)
        Task.objects.create(
            owner=missionary,
            contact=contact,
            title="Pending task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.OTHER,
            due_date=date(2026, 9, 1),
        )
        Task.objects.create(
            owner=missionary,
            contact=contact,
            title="Completed task",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.OTHER,
            due_date=date(2026, 9, 1),
            completed_at=timezone.now(),
        )
        response = _client(missionary).get(EXPORT_URL, {"status": "completed"})
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][0] == "Completed task"
        assert rows[1][2] == TaskStatus.COMPLETED

    def test_export_applies_priority_filter(self, missionary):
        contact = ContactFactory(owner=missionary)
        Task.objects.create(
            owner=missionary,
            contact=contact,
            title="High one",
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            task_type=TaskType.OTHER,
            due_date=date(2026, 10, 1),
        )
        Task.objects.create(
            owner=missionary,
            contact=contact,
            title="Low one",
            status=TaskStatus.PENDING,
            priority=TaskPriority.LOW,
            task_type=TaskType.OTHER,
            due_date=date(2026, 10, 1),
        )
        response = _client(missionary).get(EXPORT_URL, {"priority": "high"})
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][0] == "High one"
        assert rows[1][3] == TaskPriority.HIGH

    def test_export_applies_due_date_after_filter(self, missionary):
        contact = ContactFactory(owner=missionary)
        Task.objects.create(
            owner=missionary,
            contact=contact,
            title="Early",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.OTHER,
            due_date=date(2026, 1, 1),
        )
        Task.objects.create(
            owner=missionary,
            contact=contact,
            title="Late",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            task_type=TaskType.OTHER,
            due_date=date(2026, 12, 31),
        )
        response = _client(missionary).get(EXPORT_URL, {"due_date_after": "2026-06-01"})
        rows = _parse_csv(response)
        assert len(rows) == 2
        assert rows[1][0] == "Late"

    def test_export_requires_authentication(self):
        response = APIClient().get(EXPORT_URL)
        assert response.status_code == 401
