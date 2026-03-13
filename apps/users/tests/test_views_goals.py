"""
Integration test stubs for Goals API endpoint.
GOAL-02: PATCH /api/v1/goals/me/ saves monthly_support_goal_cents and goal_weeks.
GOAL-03: PATCH /api/v1/goals/me/ with journal_ids replaces GoalJournalSelection set.
"""
import pytest
from rest_framework.test import APIClient
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_patch_saves_goal_fields():
    """GOAL-02: PATCH with monetary goal returns 200 and persists the values."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.patch(
        "/api/v1/goals/me/",
        {"monthly_support_goal_cents": 350000, "goal_weeks": 52},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.monthly_support_goal_cents == 350000


@pytest.mark.django_db
def test_patch_saves_journal_selections():
    """GOAL-03: PATCH with journal_ids creates GoalJournalSelection rows; GET returns them."""
    from apps.journals.models import Journal

    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)

    j1 = Journal.objects.create(name="Journal 1", owner=user, goal_amount="1000.00")
    j2 = Journal.objects.create(name="Journal 2", owner=user, goal_amount="2000.00")

    response = client.patch(
        "/api/v1/goals/me/",
        {"journal_ids": [j1.id, j2.id]},
        format="json",
    )

    assert response.status_code == 200

    get_response = client.get("/api/v1/goals/me/")
    assert get_response.status_code == 200
    data = get_response.json()
    assert set(data["selected_journal_ids"]) == {str(j1.id), str(j2.id)}


@pytest.mark.django_db
def test_patch_journal_replace_all():
    """GOAL-03: PATCH with [id1] after [id1, id2] leaves only id1 selected."""
    from apps.journals.models import Journal

    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)

    j1 = Journal.objects.create(name="Journal 1", owner=user, goal_amount="1000.00")
    j2 = Journal.objects.create(name="Journal 2", owner=user, goal_amount="2000.00")

    # First PATCH: select both
    client.patch("/api/v1/goals/me/", {"journal_ids": [j1.id, j2.id]}, format="json")

    # Second PATCH: replace with just j1
    response = client.patch("/api/v1/goals/me/", {"journal_ids": [j1.id]}, format="json")
    assert response.status_code == 200

    get_response = client.get("/api/v1/goals/me/")
    data = get_response.json()
    assert data["selected_journal_ids"] == [str(j1.id)]


@pytest.mark.django_db
def test_get_returns_effective_monthly_support():
    """GET /api/v1/goals/me/ response includes effective_monthly_support field."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/goals/me/")
    assert response.status_code == 200
    data = response.json()
    assert "effective_monthly_support" in data


@pytest.mark.django_db
def test_unauthenticated_get_returns_401():
    """GET /api/v1/goals/me/ without auth returns 401."""
    client = APIClient()
    response = client.get("/api/v1/goals/me/")
    assert response.status_code == 401
