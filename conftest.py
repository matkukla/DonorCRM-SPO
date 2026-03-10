"""
Pytest configuration and shared fixtures.
"""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user_factory():
    """Return UserFactory for creating test users."""
    from apps.users.tests.factories import UserFactory
    return UserFactory


@pytest.fixture
def authenticated_client(user_factory):
    """Return an API client authenticated as a staff user."""
    client = APIClient()
    user = user_factory(role='missionary')
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def admin_client(user_factory):
    """Return an API client authenticated as an admin."""
    client = APIClient()
    user = user_factory(role='admin')
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def finance_client(user_factory):
    """Return an API client authenticated as a finance user."""
    client = APIClient()
    user = user_factory(role='finance')
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def admin_user(user_factory):
    """Return an admin user instance."""
    return user_factory(role='admin')


@pytest.fixture
def missionary_user(user_factory):
    """Return a missionary user instance."""
    return user_factory(role='missionary')


@pytest.fixture
def coach_user():
    """Return a coach user instance."""
    from apps.users.tests.factories import CoachUserFactory
    return CoachUserFactory()
