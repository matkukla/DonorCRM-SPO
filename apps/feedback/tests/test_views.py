"""
Tests for feedback API views.
"""
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.feedback.models import FeedbackEntry, FeedbackStatus, FeedbackType
from apps.users.tests.factories import UserFactory

LIST_URL = "/api/v1/feedback/"


def detail_url(pk) -> str:
    return f"/api/v1/feedback/{pk}/"


@pytest.mark.django_db
class TestFeedbackCreate:
    """Any authenticated user can submit feedback."""

    def test_missionary_can_submit(self):
        user = UserFactory(role="missionary")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            LIST_URL,
            {
                "type": "bug",
                "title": "It broke",
                "description": "Clicking save did nothing",
                "page_url": "/contacts/123",
            },
            HTTP_USER_AGENT="Mozilla/5.0 TestAgent",
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        entry = FeedbackEntry.objects.get(pk=response.data["id"])
        assert entry.submitter == user
        assert entry.user_agent == "Mozilla/5.0 TestAgent"
        assert entry.page_url == "/contacts/123"
        assert entry.status == FeedbackStatus.NEW

    def test_admin_can_submit(self):
        user = UserFactory(role="admin")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            LIST_URL,
            {"type": "feature", "title": "Add X", "description": "Please add X"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_unauthenticated_rejected(self):
        client = APIClient()
        response = client.post(
            LIST_URL,
            {"type": "bug", "title": "A", "description": "B"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_agent_truncated(self):
        user = UserFactory(role="missionary")
        client = APIClient()
        client.force_authenticate(user=user)

        long_agent = "X" * 1000
        response = client.post(
            LIST_URL,
            {"type": "bug", "title": "A", "description": "B"},
            HTTP_USER_AGENT=long_agent,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        entry = FeedbackEntry.objects.get(pk=response.data["id"])
        assert len(entry.user_agent) == 500

    def test_submitter_field_in_payload_is_ignored(self):
        """Even if the client tries to set submitter, the view overrides it."""
        user = UserFactory(role="missionary")
        impostor = UserFactory(role="admin")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            LIST_URL,
            {
                "type": "bug",
                "title": "A",
                "description": "B",
                "submitter": str(impostor.id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        entry = FeedbackEntry.objects.get(pk=response.data["id"])
        assert entry.submitter == user


@pytest.mark.django_db
class TestFeedbackList:
    """Only admins can list feedback."""

    def test_admin_lists_all_entries(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        FeedbackEntry.objects.create(
            submitter=m1,
            type=FeedbackType.BUG,
            title="A",
            description="x",
        )
        FeedbackEntry.objects.create(
            submitter=m2,
            type=FeedbackType.FEATURE,
            title="B",
            description="y",
        )

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_missionary_cannot_list(self):
        user = UserFactory(role="missionary")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_supervisor_cannot_list(self):
        user = UserFactory(role="supervisor")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(LIST_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_by_type(self):
        admin = UserFactory(role="admin")
        m = UserFactory(role="missionary")
        FeedbackEntry.objects.create(submitter=m, type=FeedbackType.BUG, title="A", description="x")
        FeedbackEntry.objects.create(
            submitter=m, type=FeedbackType.FEATURE, title="B", description="y"
        )
        FeedbackEntry.objects.create(submitter=m, type=FeedbackType.BUG, title="C", description="z")

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(LIST_URL, {"type": "bug"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_filter_by_status(self):
        admin = UserFactory(role="admin")
        m = UserFactory(role="missionary")
        e1 = FeedbackEntry.objects.create(
            submitter=m,
            type=FeedbackType.BUG,
            title="A",
            description="x",
        )
        FeedbackEntry.objects.create(
            submitter=m,
            type=FeedbackType.BUG,
            title="B",
            description="y",
            status=FeedbackStatus.RESOLVED,
        )

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(LIST_URL, {"status": "new"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(e1.id)

    def test_filter_by_submitter(self):
        admin = UserFactory(role="admin")
        m1 = UserFactory(role="missionary")
        m2 = UserFactory(role="missionary")
        FeedbackEntry.objects.create(
            submitter=m1, type=FeedbackType.BUG, title="A", description="x"
        )
        FeedbackEntry.objects.create(
            submitter=m2, type=FeedbackType.BUG, title="B", description="y"
        )

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get(LIST_URL, {"submitter": str(m1.id)})
        assert response.data["count"] == 1


@pytest.mark.django_db
class TestFeedbackDetail:
    def test_admin_can_update_status(self):
        admin = UserFactory(role="admin")
        m = UserFactory(role="missionary")
        entry = FeedbackEntry.objects.create(
            submitter=m,
            type=FeedbackType.BUG,
            title="A",
            description="x",
        )

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(detail_url(entry.id), {"status": "triaged"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        entry.refresh_from_db()
        assert entry.status == FeedbackStatus.TRIAGED

    def test_admin_cannot_change_immutable_fields(self):
        admin = UserFactory(role="admin")
        m = UserFactory(role="missionary")
        entry = FeedbackEntry.objects.create(
            submitter=m,
            type=FeedbackType.BUG,
            title="Original",
            description="orig",
        )

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            detail_url(entry.id),
            {"title": "Hijacked", "description": "new", "type": "feature"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        entry.refresh_from_db()
        assert entry.title == "Original"
        assert entry.description == "orig"
        assert entry.type == FeedbackType.BUG

    def test_missionary_cannot_retrieve(self):
        m = UserFactory(role="missionary")
        entry = FeedbackEntry.objects.create(
            submitter=m,
            type=FeedbackType.BUG,
            title="A",
            description="x",
        )

        # Even the original submitter should be denied (admin-only read).
        client = APIClient()
        client.force_authenticate(user=m)
        response = client.get(detail_url(entry.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Other users also denied.
        other = UserFactory(role="missionary")
        client.force_authenticate(user=other)
        response = client.get(detail_url(entry.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_delete(self):
        admin = UserFactory(role="admin")
        m = UserFactory(role="missionary")
        entry = FeedbackEntry.objects.create(
            submitter=m,
            type=FeedbackType.BUG,
            title="A",
            description="x",
        )

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.delete(detail_url(entry.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not FeedbackEntry.objects.filter(pk=entry.id).exists()
