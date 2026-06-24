"""Object-level authorization (IDOR) for the Task detail endpoint.

Every other resource (contact, gift, recurring gift, journal, prayer) has a
cross-owner fetch-by-ID test proving the queryset scoping returns 404, not the
object. Task was the lone gap. A missionary must not retrieve another
missionary's task by guessing its ID.
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.tasks.models import Task

User = get_user_model()


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def two_owner_tasks(db):
    owner = User.objects.create_user(
        email="owner-task@example.com", password="pw", role="missionary"
    )
    other = User.objects.create_user(
        email="other-task@example.com", password="pw", role="missionary"
    )
    contact = Contact.objects.create(owner=owner, first_name="Tia", last_name="Task")
    task = Task.objects.create(
        owner=owner, contact=contact, title="Private follow-up", due_date=date.today()
    )
    return {"owner": owner, "other": other, "task": task}


@pytest.mark.django_db
class TestTaskObjectLevelAuthz:
    def test_owner_can_retrieve_own_task(self, two_owner_tasks):
        resp = _client(two_owner_tasks["owner"]).get(f"/api/v1/tasks/{two_owner_tasks['task'].id}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_other_missionary_cannot_retrieve_task_by_id(self, two_owner_tasks):
        # Queryset scoping must hide the row entirely -> 404 (no existence leak).
        resp = _client(two_owner_tasks["other"]).get(f"/api/v1/tasks/{two_owner_tasks['task'].id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
