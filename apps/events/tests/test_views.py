"""
Tests for Event API views.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.events.models import Event
from apps.events.tests.factories import EventFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestEventListView:
    """Tests for event list endpoint."""

    def test_list_events_authenticated(self):
        """Test listing events for authenticated user."""
        user = UserFactory(role='staff')
        EventFactory.create_batch(3, user=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/events/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_list_events_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/v1/events/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_only_sees_own_events(self):
        """Test that users only see their own events."""
        user1 = UserFactory(role='staff')
        user2 = UserFactory(role='staff')
        EventFactory.create_batch(2, user=user1)
        EventFactory.create_batch(3, user=user2)

        client = APIClient()
        client.force_authenticate(user=user1)

        response = client.get('/api/v1/events/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2


@pytest.mark.django_db
class TestEventDetailView:
    """Tests for event detail endpoint."""

    def test_get_event_detail(self):
        """Test getting event detail."""
        user = UserFactory(role='staff')
        event = EventFactory(user=user, title='Important event')

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f'/api/v1/events/{event.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Important event'


@pytest.mark.django_db
class TestEventMarkReadView:
    """Tests for marking events as read."""

    def test_mark_event_read(self):
        """Test marking a single event as read."""
        user = UserFactory(role='staff')
        event = EventFactory(user=user, is_read=False)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f'/api/v1/events/{event.id}/read/')

        assert response.status_code == status.HTTP_200_OK
        event.refresh_from_db()
        assert event.is_read is True


@pytest.mark.django_db
class TestEventMarkAllReadView:
    """Tests for marking all events as read."""

    def test_mark_all_events_read(self):
        """Test marking all events as read."""
        user = UserFactory(role='staff')
        EventFactory.create_batch(5, user=user, is_read=False)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post('/api/v1/events/read-all/')

        assert response.status_code == status.HTTP_200_OK

        # Verify all events are now read
        unread_count = Event.objects.filter(user=user, is_read=False).count()
        assert unread_count == 0


@pytest.mark.django_db
class TestUnreadEventCountView:
    """Tests for unread event count endpoint."""

    def test_get_unread_count(self):
        """Test getting unread event count."""
        user = UserFactory(role='staff')
        EventFactory.create_batch(3, user=user, is_read=False)
        EventFactory.create_batch(2, user=user, is_read=True)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/events/unread-count/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['unread_count'] == 3
