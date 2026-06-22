"""Task contact IDOR + coach completion authorization — security report #7/#8.

#7: TaskCreateSerializer left the contact FK globally writable, so a user could
    bind a task to another owner's contact (CWE-639).
#8: Task completion used read visibility as write authority, letting a coach
    complete a coached missionary's task (CWE-862).

Each test fails if its guard is reverted (project rule #1).
"""

from datetime import date

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.contacts.models import Contact
from apps.tasks.models import Task, TaskStatus

User = get_user_model()


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def idor_setup(db):
    user_a = User.objects.create_user(
        email="a-task@example.com",
        password="pw",
        first_name="Amy",
        last_name="A",
        role="missionary",
    )
    user_b = User.objects.create_user(
        email="b-task@example.com",
        password="pw",
        first_name="Ben",
        last_name="B",
        role="missionary",
    )
    contact_a = Contact.objects.create(
        owner=user_a, first_name="Dana", last_name="Donor", email="dana.t@example.com"
    )
    return {"a": user_a, "b": user_b, "contact_a": contact_a}


@pytest.mark.django_db
class TestTaskContactIDOR:
    def test_cannot_create_task_for_foreign_contact(self, idor_setup):
        resp = _client(idor_setup["b"]).post(
            "/api/v1/tasks/",
            {
                "title": "Sneaky",
                "due_date": "2026-07-01",
                "contact": str(idor_setup["contact_a"].id),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert not Task.objects.filter(contact=idor_setup["contact_a"]).exists()

    def test_can_create_task_for_own_contact(self, idor_setup):
        resp = _client(idor_setup["a"]).post(
            "/api/v1/tasks/",
            {"title": "Mine", "due_date": "2026-07-01", "contact": str(idor_setup["contact_a"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestCoachCannotCompleteTask:
    def test_coach_cannot_complete_coached_task(self, db):
        missionary = User.objects.create_user(
            email="m-comp@example.com",
            password="pw",
            first_name="Mara",
            last_name="M",
            role="missionary",
        )
        coach = User.objects.create_user(
            email="c-comp@example.com",
            password="pw",
            first_name="Cole",
            last_name="C",
            role="coach",
        )
        coach.coached_users.add(missionary)
        task = Task.objects.create(owner=missionary, title="Call donor", due_date=date.today())

        # Coach can READ the coached task (visibility preserved)...
        list_resp = _client(coach).get("/api/v1/tasks/")
        ids = {
            r["id"]
            for r in (
                list_resp.data["results"] if isinstance(list_resp.data, dict) else list_resp.data
            )
        }
        assert str(task.id) in ids

        # ...but cannot COMPLETE it.
        resp = _client(coach).post(f"/api/v1/tasks/{task.id}/complete/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        task.refresh_from_db()
        assert task.status != TaskStatus.COMPLETED

    def test_owner_can_complete_own_task(self, db):
        missionary = User.objects.create_user(
            email="m-own@example.com",
            password="pw",
            first_name="Mara",
            last_name="M",
            role="missionary",
        )
        task = Task.objects.create(owner=missionary, title="Call donor", due_date=date.today())
        resp = _client(missionary).post(f"/api/v1/tasks/{task.id}/complete/")
        assert resp.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.status == TaskStatus.COMPLETED
